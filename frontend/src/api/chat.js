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

export async function sendMessage(token, threadId, message) {
  const res = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ thread_id: threadId, message })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to send message');
  return data;
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
