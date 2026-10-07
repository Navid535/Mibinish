import apiClient from './client';

export async function fetchSavedItems(page = 1, status, categoryId, search) {
  const params = { page };
  if (status) params.status = status;
  if (categoryId) params.category = categoryId;
  if (search) params.search = search;

  const { data } = await apiClient.get('/saved-items/', { params });
  return data;
}

export async function createSavedItem({ name, url, categoryIds = [] }) {
  const payload = {};
  if (name) payload.name = name;
  if (url) payload.url = url;
  if (categoryIds.length > 0) {
    payload.categories = categoryIds.map((id, index) => ({
      category: id,
      priority: index + 1,
    }));
  }
  const { data } = await apiClient.post('/saved-items/', payload);
  return data;
}

export async function updateSavedItem(id, payload) {
  const { data } = await apiClient.patch(`/saved-items/${id}/`, payload);
  return data;
}

export async function deleteSavedItem(id) {
  await apiClient.delete(`/saved-items/${id}/`);
}