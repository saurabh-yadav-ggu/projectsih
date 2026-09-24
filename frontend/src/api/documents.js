const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchGeneratedDocuments(token) {
  const res = await fetch(`${API_BASE_URL}/api/documents/generated`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch generated documents');
  }
  return res.json();
}

export async function deleteGeneratedDocument(token, filename) {
  const res = await fetch(`${API_BASE_URL}/api/documents/generated/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to delete document');
  }
  return res.json();
}

export function getDocumentDownloadUrl(filePath, token = null) {
  const encodedPath = encodeURIComponent(filePath);
  const tokenParam = token ? `&token=${encodeURIComponent(token)}` : '';
  return `${API_BASE_URL}/api/documents/download?path=${encodedPath}${tokenParam}`;
}

export async function downloadDocumentFile(token, filePath, suggestedFilename = null) {
  const url = `${API_BASE_URL}/api/documents/download?path=${encodeURIComponent(filePath)}`;
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(url, { headers });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to download document');
  }
  const blob = await res.blob();
  const filename = suggestedFilename || filePath.split(/[\\/]/).pop() || 'document';
  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
}
