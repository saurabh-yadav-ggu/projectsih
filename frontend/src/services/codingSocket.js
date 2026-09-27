class CodingSocketService {
  constructor() {
    this.ws = null;
    this.token = null;
    this.reconnectTimer = null;
    this.listeners = new Map();
    this.sessionId = 'default';
  }

  setToken(token) {
    this.token = token;
  }

  setSessionId(sessionId) {
    this.sessionId = sessionId || 'default';
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);
    return () => this.listeners.get(event)?.delete(callback);
  }

  emit(event, data) {
    const cbs = this.listeners.get(event);
    if (cbs) {
      cbs.forEach((cb) => {
        try {
          cb(data);
        } catch (err) {
          console.error(`Error in codingSocket listener for ${event}:`, err);
        }
      });
    }
  }

  connect(token = null) {
    if (token) {
      this.token = token;
    } else if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem('token');
    }

    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const host = window.location.hostname || 'localhost';
    const port = '8000'; // FastAPI backend port
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const query = this.token ? `?token=${encodeURIComponent(this.token)}` : '';
    const url = `${protocol}//${host}:${port}/ws/coding${query}`;

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log('Connected to Coding Agent WebSocket');
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
        this.emit('connected', true);
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          this.handleEvent(msg);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      this.ws.onclose = () => {
        this.emit('connected', false);
        this.emit('agent_status', { status: 'idle' });
        this.reconnectTimer = setTimeout(() => {
          if (this.token) this.connect();
        }, 3000);
      };

      this.ws.onerror = (err) => {
        console.error('Coding WebSocket error:', err);
        this.emit('connected', false);
      };
    } catch (err) {
      console.error('WebSocket connection failed:', err);
      this.reconnectTimer = setTimeout(() => {
        if (this.token) this.connect();
      }, 3000);
    }
  }

  handleEvent(msg) {
    switch (msg.type) {
      case 'agent_status':
        this.emit('agent_status', msg);
        break;
      case 'agent_chunk':
        this.emit('agent_chunk', msg);
        break;
      case 'tool_started':
        this.emit('tool_started', msg);
        break;
      case 'tool_finished':
        this.emit('tool_finished', msg);
        break;
      case 'file_changed':
        this.emit('file_changed', msg);
        break;
      case 'agent_approval_required':
      case 'approval_required':
        this.emit('agent_approval_required', msg);
        this.emit('approval_required', msg);
        break;
      case 'hitl_mode_updated':
        this.emit('hitl_mode_updated', msg);
        break;
      case 'agent_completed':
        this.emit('agent_completed', msg);
        break;
      case 'workspace_selected':
        this.emit('workspace_selected', msg);
        break;
      case 'error':
        this.emit('error', msg);
        break;
      default:
        this.emit(msg.type, msg);
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('Coding WebSocket is not open. Reconnecting...');
      this.connect();
      setTimeout(() => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify(data));
        }
      }, 500);
    }
  }

  sendPrompt(text, model = 'default', workspacePath = null, sessionId = null, hitlMode = 'safe') {
    const sid = sessionId || this.sessionId;
    this.send({
      type: 'prompt',
      session_id: sid,
      text,
      model,
      workspace_path: workspacePath,
      hitl_mode: hitlMode,
      token: this.token,
    });
  }

  setHitlMode(mode, sessionId = null) {
    const sid = sessionId || this.sessionId;
    this.send({
      type: 'set_hitl_mode',
      session_id: sid,
      mode,
    });
  }

  sendApproval(requestId, decision, sessionId = null) {
    const sid = sessionId || this.sessionId;
    this.send({
      type: 'approval_response',
      session_id: sid,
      request_id: requestId,
      decision,
    });
  }

  stop(sessionId = null) {
    const sid = sessionId || this.sessionId;
    this.send({
      type: 'stop',
      session_id: sid,
    });
  }

  selectWorkspace(path, sessionId = null) {
    const sid = sessionId || this.sessionId;
    this.send({
      type: 'select_workspace',
      session_id: sid,
      path,
    });
  }

  reset(sessionId = null) {
    const sid = sessionId || this.sessionId;
    this.send({
      type: 'reset',
      session_id: sid,
    });
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const codingSocket = new CodingSocketService();
