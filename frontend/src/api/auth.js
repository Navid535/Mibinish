import apiClient from './client';
import * as SecureStore from 'expo-secure-store';

export async function login(email, password) {
  const { data } = await apiClient.post('/auth/token/', { email, password });
  await SecureStore.setItemAsync('access_token', data.access);
  await SecureStore.setItemAsync('refresh_token', data.refresh);
  return data;
}

export async function register(email, firstName, password) {
  const { data } = await apiClient.post('/auth/register/', {
    email,
    first_name: firstName,
    password,
  });
  await SecureStore.setItemAsync('access_token', data.access);
  await SecureStore.setItemAsync('refresh_token', data.refresh);
  return data;
}

export async function logout() {
  await SecureStore.deleteItemAsync('access_token');
  await SecureStore.deleteItemAsync('refresh_token');
}
