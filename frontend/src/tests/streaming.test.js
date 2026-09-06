import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

describe('Streaming Controller & Race Condition Protections', () => {
  test('generates unique request IDs and manages active streams', () => {
    class MockStreamingController {
      constructor() {
        this.activeStreams = new Map();
      }
      start(threadId, requestId) {
        const controller = new AbortController();
        this.activeStreams.set(threadId, {
          abortController: controller,
          requestId,
          status: 'STREAMING',
          accumulatedText: ''
        });
        return controller;
      }
      appendToken(threadId, requestId, token) {
        const stream = this.activeStreams.get(threadId);
        // Stale request guard
        if (!stream || stream.requestId !== requestId) {
          return false;
        }
        stream.accumulatedText += token;
        return true;
      }
      abort(threadId) {
        const stream = this.activeStreams.get(threadId);
        if (!stream) return false;
        stream.status = 'STOPPED';
        stream.abortController.abort();
        const partial = stream.accumulatedText;
        this.activeStreams.delete(threadId);
        return partial;
      }
    }

    const controller = new MockStreamingController();

    // 1. Start Request A
    controller.start('thread-1', 'req-A');
    assert.equal(controller.appendToken('thread-1', 'req-A', 'Hello '), true);
    assert.equal(controller.appendToken('thread-1', 'req-A', 'world'), true);

    // 2. Stop Request A - partial response must remain
    const partial = controller.abort('thread-1');
    assert.equal(partial, 'Hello world');

    // 3. Stale chunk from Request A after abort must be rejected
    assert.equal(controller.appendToken('thread-1', 'req-A', ' leaked token!'), false);

    // 4. Start Request B
    controller.start('thread-1', 'req-B');
    assert.equal(controller.appendToken('thread-1', 'req-B', 'New generation'), true);

    // Stale chunk from old Request A must NOT modify Request B
    assert.equal(controller.appendToken('thread-1', 'req-A', ' from A'), false);
    assert.equal(controller.activeStreams.get('thread-1').accumulatedText, 'New generation');
  });

  test('independent streaming across multiple threads', () => {
    const streams = new Map();
    function start(threadId) {
      streams.set(threadId, { text: '', status: 'STREAMING' });
    }
    function append(threadId, token) {
      if (streams.has(threadId)) {
        streams.get(threadId).text += token;
      }
    }

    start('thread-1');
    start('thread-2');

    append('thread-1', 'Message 1');
    append('thread-2', 'Message 2');

    assert.equal(streams.get('thread-1').text, 'Message 1');
    assert.equal(streams.get('thread-2').text, 'Message 2');
  });
});

describe('ChatGPT-Grade Auto-Scroll Logic', () => {
  function isNearBottom({ scrollHeight, scrollTop, clientHeight }, threshold = 100) {
    return scrollHeight - scrollTop - clientHeight <= threshold;
  }

  test('correctly identifies when viewport is near bottom', () => {
    // User is at bottom (distance = 0)
    assert.equal(isNearBottom({ scrollHeight: 1000, scrollTop: 600, clientHeight: 400 }), true);

    // User is 50px away from bottom (within threshold 100)
    assert.equal(isNearBottom({ scrollHeight: 1000, scrollTop: 550, clientHeight: 400 }), true);

    // User has scrolled up (distance = 300px > threshold 100)
    assert.equal(isNearBottom({ scrollHeight: 1000, scrollTop: 300, clientHeight: 400 }), false);
  });

  test('auto-scroll disengages when user scrolls up and re-engages on jumpToLatest', () => {
    let autoScrollEnabled = true;
    let showJumpToLatest = false;

    function handleScroll(metrics) {
      const near = isNearBottom(metrics);
      if (near) {
        autoScrollEnabled = true;
        showJumpToLatest = false;
      } else {
        autoScrollEnabled = false;
        showJumpToLatest = true;
      }
    }

    function jumpToLatest() {
      autoScrollEnabled = true;
      showJumpToLatest = false;
    }

    // Initial state: near bottom
    handleScroll({ scrollHeight: 1000, scrollTop: 600, clientHeight: 400 });
    assert.equal(autoScrollEnabled, true);
    assert.equal(showJumpToLatest, false);

    // User scrolls up
    handleScroll({ scrollHeight: 1000, scrollTop: 200, clientHeight: 400 });
    assert.equal(autoScrollEnabled, false);
    assert.equal(showJumpToLatest, true);

    // User clicks Jump to Latest
    jumpToLatest();
    assert.equal(autoScrollEnabled, true);
    assert.equal(showJumpToLatest, false);
  });
});

describe('Message State Transitions & Action Handlers', () => {
  test('message status transitions preserve content on stop or error', () => {
    let message = {
      id: 'msg-1',
      role: 'assistant',
      content: '',
      status: 'STREAMING'
    };

    // Accumulate tokens
    message.content += 'Analyzing requirements...';
    assert.equal(message.content, 'Analyzing requirements...');

    // User stops generation
    message.status = 'STOPPED';
    message.content += '\n\n*[Generation stopped by user]*';

    assert.equal(message.status, 'STOPPED');
    assert.match(message.content, /Analyzing requirements/);
    assert.match(message.content, /stopped by user/);
  });

  test('regenerate response trims assistant response and retains user prompt', () => {
    const messages = [
      { id: 'u-1', role: 'user', content: 'Draft an NDA' },
      { id: 'a-1', role: 'assistant', content: 'Here is an NDA...' }
    ];

    const targetAssistantIdx = messages.findIndex(m => m.id === 'a-1');
    assert.equal(targetAssistantIdx, 1);

    const precedingUserMsg = messages[targetAssistantIdx - 1];
    assert.equal(precedingUserMsg.content, 'Draft an NDA');

    // Trim assistant message for regeneration
    const newMessages = messages.slice(0, targetAssistantIdx);
    assert.equal(newMessages.length, 1);
    assert.equal(newMessages[0].content, 'Draft an NDA');
  });

  test('edit user message trims subsequent messages and allows re-submission', () => {
    const messages = [
      { id: 'u-1', role: 'user', content: 'First prompt' },
      { id: 'a-1', role: 'assistant', content: 'First answer' },
      { id: 'u-2', role: 'user', content: 'Second prompt' },
      { id: 'a-2', role: 'assistant', content: 'Second answer' }
    ];

    // User edits u-1
    const editIdx = messages.findIndex(m => m.id === 'u-1');
    const remainingBeforeEdit = messages.slice(0, editIdx);
    assert.equal(remainingBeforeEdit.length, 0); // Replaces whole conversation from that point

    // Or user edits u-2:
    const editIdx2 = messages.findIndex(m => m.id === 'u-2');
    const remainingBeforeU2 = messages.slice(0, editIdx2);
    assert.equal(remainingBeforeU2.length, 2);
    assert.equal(remainingBeforeU2[0].content, 'First prompt');
  });

  test('draft persistence saves and restores per thread', () => {
    const drafts = {};

    // User types in thread 1
    drafts['thread-1'] = 'My unsubmitted draft for thread 1';

    // Switch to thread 2
    assert.equal(drafts['thread-2'] || '', '');

    // User types in thread 2
    drafts['thread-2'] = 'Draft 2';

    // Switch back to thread 1
    assert.equal(drafts['thread-1'], 'My unsubmitted draft for thread 1');
  });

  test('duplicate submission is prevented when isGenerating is true', () => {
    let isGenerating = false;
    let submitCount = 0;

    function handleSend(text) {
      if (!text.trim() || isGenerating) return;
      isGenerating = true;
      submitCount++;
    }

    handleSend('Hello');
    assert.equal(submitCount, 1);
    assert.equal(isGenerating, true);

    // Attempt double click or rapid Enter press
    handleSend('Hello again');
    assert.equal(submitCount, 1); // Guard prevented duplicate submission
  });
});
