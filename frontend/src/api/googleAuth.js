import { GoogleSignin } from '@react-native-google-signin/google-signin';
import * as SecureStore from 'expo-secure-store';

import apiClient from './client';

GoogleSignin.configure({
  webClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID,
});

export async function signInWithGoogle() {
  await GoogleSignin.hasPlayServices({
    showPlayServicesUpdateDialog: true,
  });

  const response = await GoogleSignin.signIn();

  if (response?.type === 'cancelled') {
    return null;
  }

  const idToken = response?.data?.idToken ?? response?.idToken;

  if (!idToken) {
    throw new Error('Google did not return an ID token');
  }

  const { data } = await apiClient.post('/auth/google/', {
    id_token: idToken,
  });

  await SecureStore.setItemAsync('access_token', data.access);
  await SecureStore.setItemAsync('refresh_token', data.refresh);

  return data;
}

export async function signOutFromGoogle() {
  try {
    await GoogleSignin.signOut();
  } catch (error) {
    console.warn('Google sign-out failed:', error);
  }
}