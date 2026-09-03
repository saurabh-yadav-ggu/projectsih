const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function loginUser(email, password) {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Login failed');
  }
  return data;
}

export async function registerUser({ name, email, organisation, designation, password }) {
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, organisation, designation, password })
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Registration failed');
  }
  return data;
}

export async function fetchCurrentUser(token) {
  const res = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  if (!res.ok) {
    throw new Error('Token invalid');
  }
  return await res.json();
}
