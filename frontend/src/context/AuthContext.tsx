import React, { createContext, useContext, useEffect, useState } from 'react';
import * as SecureStore from 'expo-secure-store';

import { signInWithGoogle, signOutFromGoogle } from '../api/googleAuth';
import { login as apiLogin, register as apiRegister, logout as apiLogout } from '../api/auth';
import { setSessionExpiredHandler } from '../api/client';

type AuthContextType = {
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, firstName: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  loginWithGoogle: () => Promise<boolean>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    SecureStore.getItemAsync('access_token').then((token) => {
      setIsAuthenticated(!!token);
      setIsLoading(false);
    });
  }, []);

  useEffect(() => {
    setSessionExpiredHandler(() => setIsAuthenticated(false));
    return () => setSessionExpiredHandler(null);
  }, []);



  const login = async (email: string, password: string) => {
    await apiLogin(email, password);
    setIsAuthenticated(true);
  };

  const register = async (email: string, firstName: string, password: string) => {
    await apiRegister(email, firstName, password);
    setIsAuthenticated(true);
  };

  const logout = async () => {
    try {
      await apiLogout();
    } finally {
      await signOutFromGoogle();
      setIsAuthenticated(false);
    }
  };

  const loginWithGoogle = async () => {
    const result = await signInWithGoogle();
    if (!result) return false;
    setIsAuthenticated(true);
    return true;
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, login, register, logout, loginWithGoogle }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}