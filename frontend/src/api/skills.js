const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchSkills(token, category = null) {
  const url = new URL(`${API_BASE_URL}/api/skills`);
  if (category && category !== 'all') {
    url.searchParams.append('category', category);
  }
  const res = await fetch(url.toString(), {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to fetch skills');
  return data;
}

export async function fetchSkill(token, skillId) {
  const res = await fetch(`${API_BASE_URL}/api/skills/${encodeURIComponent(skillId)}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Failed to fetch skill: ${skillId}`);
  return data;
}

export async function createSkill(token, skillData) {
  const res = await fetch(`${API_BASE_URL}/api/skills`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(skillData)
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to create skill');
  return data;
}

export async function updateSkill(token, skillId, skillData) {
  const res = await fetch(`${API_BASE_URL}/api/skills/${encodeURIComponent(skillId)}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(skillData)
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to update skill');
  return data;
}

export async function deleteSkill(token, skillId) {
  const res = await fetch(`${API_BASE_URL}/api/skills/${encodeURIComponent(skillId)}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to delete skill');
  return data;
}
