import Constants from 'expo-constants';

function getDevApiUrl() {
  const hostUri =
    Constants.expoConfig?.hostUri ??
    Constants.manifest2?.extra?.expoClient?.hostUri ??
    Constants.manifest?.debuggerHost;

  if (!hostUri) return null;

  const host = hostUri.split(':')[0];
  return `http://${host}:8000/api/v1`;
}

const PROD_API_URL = process.env.EXPO_PUBLIC_API_URL; 
export const API_BASE_URL = __DEV__
  ? getDevApiUrl() ?? 'http://localhost:8000/api/v1'
  : PROD_API_URL;
