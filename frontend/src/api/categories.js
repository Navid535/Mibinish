import apiClient from './client';

export async function fetchCategories() {
  const { data } = await apiClient.get('/categories/');
  return data.results ?? data; // اگه CategoryViewSet هم paginate باشه یا نباشه، هر دو کار می‌کنه
}

export async function createCategory({ name, color }) {
  const { data } = await apiClient.post('/categories/', { name, color });
  return data;
}

export async function deleteCategory(id) {
  await apiClient.delete(`/categories/${id}/`);
}