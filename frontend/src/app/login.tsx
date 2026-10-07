import React, { useState } from 'react';
import {
  ImageBackground,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/Button';
import { TextInput } from '@/components/ui/TextInput';
import { Colors, Spacing } from '@/constants/theme';
import { Card } from '@/components/ui/Card';
import { getErrorMessage } from '@/utils/errors';

const backgroundImage = require('@/assets/images/login-background.jpg');

export default function LoginScreen() {
  const [isRegistering, setIsRegistering] = useState(false);

  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');

  const { login, register } = useAuth();

  const handleSubmit = async () => {
    setError('');

    if (!email.trim() || !password) {
      setError('Email and password are required.');
      return;
    }

    if (isRegistering) {
      if (!firstName.trim()) {
        setError('First name is required.');
        return;
      }

      if (password !== confirmPassword) {
        setError('Passwords do not match.');
        return;
      }
    }

    try {
      if (isRegistering) {
        await register(email.trim(), firstName.trim(), password);
      } else {
        await login(email.trim(), password);
      }
    } catch (err: any) {
      setError(
        getErrorMessage(
          err,
          isRegistering
            ? 'Registration failed. Check your information and try again.'
            : 'Login failed. Check your email and password.',
        ),
      );
    }
  };

  const switchMode = () => {
    setIsRegistering((value) => !value);
    setError('');
    setPassword('');
    setConfirmPassword('');
  };

  return (
    <ImageBackground
      source={backgroundImage}
      style={styles.background}
      resizeMode="cover"
    >
      <View style={styles.overlay}>
        <Card variant="glass">
          <Text style={styles.title}>Mibinish</Text>

          <Text style={styles.heading}>
            {isRegistering ? 'Create account' : 'Welcome back'}
          </Text>

          {isRegistering ? (
            <TextInput
              placeholder="First name"
              value={firstName}
              onChangeText={setFirstName}
              autoCapitalize="words"
            />
          ) : null}

          <TextInput
            placeholder="Email"
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
          />

          <TextInput
            placeholder="Password"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />

          {isRegistering ? (
            <TextInput
              placeholder="Confirm password"
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              secureTextEntry
            />
          ) : null}

          {error ? (
            <Text style={styles.error}>{error}</Text>
          ) : null}

          <Button
            title={isRegistering ? 'Create account' : 'Login'}
            onPress={handleSubmit}
          />

          <View style={styles.switchContainer}>
            <Text style={styles.switchText}>
              {isRegistering
                ? 'Already have an account?'
                : "Don't have an account?"}
            </Text>

            <Button
              title={isRegistering ? 'Login' : 'Sign up'}
              variant="secondary"
              onPress={switchMode}
            />
          </View>
        </Card>
      </View>
    </ImageBackground>
  );
}

const styles = StyleSheet.create({
  background: {
    flex: 1,
  },

  overlay: {
    flex: 1,
    backgroundColor: 'rgba(248, 224, 164, 0.35)',
    justifyContent: 'center',
    padding: Spacing.four,
  },

  card: {
    backgroundColor: 'rgba(255,255,255,0.92)',
    borderRadius: 28,
    padding: Spacing.five,
    gap: Spacing.three,
  },

  title: {
    fontFamily: 'InterBold',
    fontSize: 34,
    color: Colors.light.primary,
    textAlign: 'center',
  },

  heading: {
    fontFamily: 'InterSemiBold',
    fontSize: 22,
    color: Colors.light.text,
    textAlign: 'center',
    marginBottom: Spacing.two,
  },

  error: {
    fontFamily: 'Inter',
    color: Colors.light.danger,
    textAlign: 'center',
  },

  switchContainer: {
    alignItems: 'center',
    gap: Spacing.two,
    marginTop: Spacing.two,
  },

  switchText: {
    fontFamily: 'Inter',
    color: Colors.light.textSecondary,
  },
});