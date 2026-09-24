const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function createThread(token, title = 'New conversation') {
  const res = await fetch(`${API_BASE_URL}/api/threads`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ title })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to create thread');
  return data;
}

export async function fetchThreads(token) {
  const res = await fetch(`${API_BASE_URL}/api/threads`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to fetch threads');
  return data;
}

export async function fetchThreadMessages(token, threadId) {
  const res = await fetch(`${API_BASE_URL}/api/threads/${threadId}/messages`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to fetch messages');
  return data;
}

export async function deleteThread(token, threadId) {
  const res = await fetch(`${API_BASE_URL}/api/threads/${threadId}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!res.ok) throw new Error('Failed to delete thread');
  return true;
}

export async function sendMessage(token, threadId, message, imagePath = null) {
  const res = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ thread_id: threadId, message, image_path: imagePath || null })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to send message');
  return data;
}

export async function sendMessageStream(
  token,
  threadId,
  message,
  {
    onInit,
    onToken,
    onPlan,
    onSubagentStart,
    onSubagentResult,
    onToolStart,
    onToolEnd,
    onArtifactCreated,
    onVerification,
    onDone,
    onError,
    onAbort,
    signal
  } = {}
) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ thread_id: threadId || null, message }),
      signal
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: 'Streaming request failed' }));
      throw new Error(errData.detail || 'Streaming request failed');
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      if (signal?.aborted) break;

      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete trailing fragment

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data: ')) continue;

        const jsonStr = trimmed.substring(6).trim();
        if (!jsonStr) continue;

        try {
          const data = JSON.parse(jsonStr);
          if (data.type === 'init' && onInit) {
            onInit(data);
          } else if (data.type === 'token' && onToken) {
            onToken(data.content);
          } else if (data.type === 'plan' && onPlan) {
            onPlan(data.plan);
          } else if (data.type === 'subagent_start' && onSubagentStart) {
            onSubagentStart(data);
          } else if (data.type === 'subagent_result' && onSubagentResult) {
            onSubagentResult(data);
          } else if (data.type === 'tool_start' && onToolStart) {
            onToolStart(data);
          } else if (data.type === 'tool_end' && onToolEnd) {
            onToolEnd(data);
          } else if (data.type === 'artifact_created' && onArtifactCreated) {
            onArtifactCreated(data);
          } else if (data.type === 'verification' && onVerification) {
            onVerification(data);
          } else if (data.type === 'done' && onDone) {
            onDone(data);
          } else if (data.type === 'error' && onError) {
            onError(new Error(data.error));
          }
        } catch (e) {
          console.warn('Error parsing stream packet:', e);
        }
      }
    }
  } catch (err) {
    if (err.name === 'AbortError' || signal?.aborted) {
      if (onAbort) onAbort();
      return;
    }
    if (onError) onError(err);
  }
}

export async function fetchMemories(token) {
  const res = await fetch(`${API_BASE_URL}/api/memory`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to fetch memories');
  return data;
}

export async function deleteMemory(token, memoryId) {
  const res = await fetch(`${API_BASE_URL}/api/memory/${memoryId}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!res.ok) throw new Error('Failed to delete memory');
  return true;
}

export async function uploadDocument(token, file, threadId = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (threadId) {
    formData.append('thread_id', threadId);
  }

  const res = await fetch(`${API_BASE_URL}/api/upload`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to upload document');
  return data;
}

export async function downloadDocument(token, filePath) {
  const res = await fetch(`${API_BASE_URL}/api/documents/download?path=${encodeURIComponent(filePath)}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to download document');
  }
  return res;
}
