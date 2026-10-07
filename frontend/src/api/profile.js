import apiClient from './client';

export async function fetchProfile() {
  const { data } = await apiClient.get('/auth/me/');
  return data;
}

export async function updateRetentionDays(days) {
  const { data } = await apiClient.patch('/auth/me/', {
    completed_items_retention_days: days,
  });
  return data;
}

export async function changePassword(oldPassword, newPassword) {
  await apiClient.put('/auth/me/change-password/', {
    old_password: oldPassword,
    new_password: newPassword,
  });
}
