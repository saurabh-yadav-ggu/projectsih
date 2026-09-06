/**
 * Streaming Controller Service
 * Manages per-thread AbortControllers, unique requestIds, SSE parsing,
 * and eliminates race conditions between canceled and new generations.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function generateRequestId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

class StreamingController {
  constructor() {
    // Map of threadId -> { abortController, requestId, status, accumulatedText }
    this.activeStreams = new Map();
  }

  isStreaming(threadId) {
    const stream = this.activeStreams.get(threadId);
    return stream ? stream.status === 'STREAMING' : false;
  }

  getActiveRequestId(threadId) {
    return this.activeStreams.get(threadId)?.requestId || null;
  }

  abortStream(threadId) {
    const stream = this.activeStreams.get(threadId);
    if (!stream) return false;

    try {
      stream.status = 'STOPPED';
      stream.abortController.abort('User stopped generation');
    } catch (e) {
      console.warn('Error aborting stream:', e);
    }

    // Call onAbort callback if present
    if (typeof stream.onAbort === 'function') {
      stream.onAbort(stream.accumulatedText);
    }

    this.activeStreams.delete(threadId);
    return true;
  }

  async startStream({
    token,
    threadId,
    message,
    onInit,
    onToken,
    onToolStart,
    onToolEnd,
    onDone,
    onError,
    onAbort
  }) {
    // If an existing stream is active for this thread, abort it first cleanly
    if (this.isStreaming(threadId)) {
      this.abortStream(threadId);
    }

    const abortController = new AbortController();
    const requestId = generateRequestId();

    const streamState = {
      abortController,
      requestId,
      status: 'STREAMING',
      accumulatedText: '',
      onAbort
    };

    this.activeStreams.set(threadId, streamState);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          thread_id: threadId || null,
          message
        }),
        signal: abortController.signal
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Streaming request failed' }));
        throw new Error(errorData.detail || `Server returned ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        // Check if stream was aborted mid-read
        if (abortController.signal.aborted) {
          break;
        }

        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete trailing fragment

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data: ')) continue;

          const jsonStr = trimmed.slice(6).trim();
          if (!jsonStr) continue;

          try {
            const data = JSON.parse(jsonStr);

            // Stale request guard: ensure this event belongs to the active requestId
            const current = this.activeStreams.get(threadId);
            if (!current || current.requestId !== requestId) {
              return; // Ignore chunks from stale/abandoned requests
            }

            if (data.type === 'init') {
              if (onInit) onInit(data);
            } else if (data.type === 'token') {
              streamState.accumulatedText += data.content;
              if (onToken) onToken(data.content, streamState.accumulatedText);
            } else if (data.type === 'tool_start') {
              if (onToolStart) onToolStart(data);
            } else if (data.type === 'tool_end') {
              if (onToolEnd) onToolEnd(data);
            } else if (data.type === 'done') {
              streamState.status = 'COMPLETED';
              const finalMessage = data.message || streamState.accumulatedText;
              if (onDone) onDone({ ...data, message: finalMessage });
              this.activeStreams.delete(threadId);
              return;
            } else if (data.type === 'error') {
              streamState.status = 'ERROR';
              if (onError) onError(new Error(data.error || 'Unknown streaming error'), streamState.accumulatedText);
              this.activeStreams.delete(threadId);
              return;
            }
          } catch (parseErr) {
            console.warn('Failed to parse SSE line:', line, parseErr);
          }
        }
      }

      // If finished stream normally without explicit done event
      const current = this.activeStreams.get(threadId);
      if (current && current.requestId === requestId && current.status === 'STREAMING') {
        current.status = 'COMPLETED';
        if (onDone) {
          onDone({ thread_id: threadId, message: streamState.accumulatedText });
        }
        this.activeStreams.delete(threadId);
      }
    } catch (err) {
      const isAbort = err.name === 'AbortError' || abortController.signal.aborted;

      if (isAbort) {
        streamState.status = 'STOPPED';
        if (onAbort) {
          onAbort(streamState.accumulatedText);
        }
      } else {
        streamState.status = 'ERROR';
        if (onError) {
          onError(err, streamState.accumulatedText);
        }
      }
      this.activeStreams.delete(threadId);
    }
  }
}

export const streamingController = new StreamingController();
export default streamingController;
