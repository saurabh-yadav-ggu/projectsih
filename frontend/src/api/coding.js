const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function getHeaders(token) {
  const authToken = token || (typeof window !== 'undefined' ? localStorage.getItem('token') : null);
  const headers = { 'Content-Type': 'application/json' };
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
  return headers;
}

export async function createCodingSession(token, workspacePath = null, title = 'Coding Session', model = null, conversationId = null) {
  const res = await fetch(`${API_BASE_URL}/api/coding/sessions`, {
    method: 'POST',
    headers: getHeaders(token),
    body: JSON.stringify({
      workspace_path: workspacePath,
      title,
      model,
      conversation_id: conversationId,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to create coding session');
  return data;
}

export async function listCodingSessions(token) {
  const res = await fetch(`${API_BASE_URL}/api/coding/sessions`, {
    headers: getHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to list coding sessions');
  return data;
}

export async function getCodingSession(token, sessionId) {
  const res = await fetch(`${API_BASE_URL}/api/coding/sessions/${sessionId}`, {
    headers: getHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to get coding session');
  return data;
}

export async function deleteCodingSession(token, sessionId) {
  const res = await fetch(`${API_BASE_URL}/api/coding/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: getHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to delete coding session');
  return true;
}

export async function fetchWorkspaceTree(token, sessionId = null) {
  const url = new URL(`${API_BASE_URL}/api/coding/workspace/tree`);
  if (sessionId) url.searchParams.append('session_id', sessionId);
  const res = await fetch(url.toString(), {
    headers: getHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to fetch file tree');
  return data;
}

export async function readWorkspaceFile(token, filePath, sessionId = null) {
  const url = new URL(`${API_BASE_URL}/api/coding/workspace/file`);
  url.searchParams.append('path', filePath);
  if (sessionId) url.searchParams.append('session_id', sessionId);
  const res = await fetch(url.toString(), {
    headers: getHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Failed to read file ${filePath}`);
  return data;
}

export async function writeWorkspaceFile(token, filePath, content, sessionId = null) {
  const url = new URL(`${API_BASE_URL}/api/coding/workspace/file`);
  if (sessionId) url.searchParams.append('session_id', sessionId);
  const res = await fetch(url.toString(), {
    method: 'POST',
    headers: getHeaders(token),
    body: JSON.stringify({ path: filePath, content }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Failed to write file ${filePath}`);
  return data;
}

export async function deleteWorkspaceFile(token, filePath, sessionId = null) {
  const url = new URL(`${API_BASE_URL}/api/coding/workspace/file`);
  url.searchParams.append('path', filePath);
  if (sessionId) url.searchParams.append('session_id', sessionId);
  const res = await fetch(url.toString(), {
    method: 'DELETE',
    headers: getHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to delete file ${filePath}`);
  return true;
}

export async function renameWorkspaceFile(token, oldPath, newPath, sessionId = null) {
  const url = new URL(`${API_BASE_URL}/api/coding/workspace/file`);
  if (sessionId) url.searchParams.append('session_id', sessionId);
  const res = await fetch(url.toString(), {
    method: 'PATCH',
    headers: getHeaders(token),
    body: JSON.stringify({ old_path: oldPath, new_path: newPath }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to rename file');
  return data;
}

export async function fetchWorkspaceGit(token, sessionId = null) {
  const url = new URL(`${API_BASE_URL}/api/coding/workspace/git`);
  if (sessionId) url.searchParams.append('session_id', sessionId);
  const res = await fetch(url.toString(), {
    headers: getHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to fetch git status');
  return data;
}

export async function fetchWorkspaceActive(token, sessionId = null) {
  const url = new URL(`${API_BASE_URL}/api/coding/workspace/active`);
  if (sessionId) url.searchParams.append('session_id', sessionId);
  const res = await fetch(url.toString(), {
    headers: getHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to fetch active workspace');
  return data;
}

export async function fetchSuggestedWorkspaces(token) {
  const url = new URL(`${API_BASE_URL}/api/coding/workspace/list`);
  const res = await fetch(url.toString(), {
    headers: getHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to list workspaces');
  return data;
}

export async function browseDirectories(token, path = null) {
  const url = new URL(`${API_BASE_URL}/api/coding/workspace/browse`);
  if (path) url.searchParams.append('path', path);
  const res = await fetch(url.toString(), {
    headers: getHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to browse directories');
  return data;
}


export async function selectActiveWorkspace(token, path, sessionId = 'default', createIfMissing = true) {
  const url = new URL(`${API_BASE_URL}/api/coding/workspace/select`);
  if (sessionId) url.searchParams.append('session_id', sessionId);
  const res = await fetch(url.toString(), {
    method: 'POST',
    headers: getHeaders(token),
    body: JSON.stringify({ path, create_if_missing: createIfMissing }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to switch workspace');
  return data;
}

export async function fetchTerminalInfo(token, sessionId = 'default') {
  const url = new URL(`${API_BASE_URL}/api/coding/terminal/info`);
  url.searchParams.append('session_id', sessionId);
  const res = await fetch(url.toString(), {
    headers: getHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to fetch terminal info');
  return data;
}

export async function executeTerminalCommand(token, command, cwd = null, sessionId = 'default') {
  const url = new URL(`${API_BASE_URL}/api/coding/terminal/exec`);
  url.searchParams.append('session_id', sessionId);
  const res = await fetch(url.toString(), {
    method: 'POST',
    headers: getHeaders(token),
    body: JSON.stringify({ command, cwd }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to execute command');
  return data;
}

export async function submitApprovalDecision(token, sessionId, requestId, decision) {
  const url = new URL(`${API_BASE_URL}/api/coding/approval`);
  url.searchParams.append('session_id', sessionId);
  const res = await fetch(url.toString(), {
    method: 'POST',
    headers: getHeaders(token),
    body: JSON.stringify({ request_id: requestId, decision }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to submit approval decision');
  return data;
}

export async function fetchCodingSessionMessages(token, sessionId) {
  const res = await fetch(`${API_BASE_URL}/api/coding/sessions/${sessionId}/messages`, {
    headers: getHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to fetch session messages');
  return data;
}
