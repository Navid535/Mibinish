// src/components/profile-modal.tsx
import { useEffect, useState } from 'react';
import { Modal, ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';

import { changePassword, fetchProfile, setPassword, updateRetentionDays } from '@/api/profile';
import { ThemedText } from '@/components/themed-text';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { TextInput } from '@/components/ui/TextInput';
import { Colors, Spacing } from '@/constants/theme';
import { useAuth } from '@/context/AuthContext';
import { getErrorMessage } from '@/utils/errors';

type Props = {
  visible: boolean;
  onClose: () => void;
};

export function ProfileModal({ visible, onClose }: Props) {
  const { logout } = useAuth();
  const [profile, setProfile] = useState<any | null>(null);
  const [loadError, setLoadError] = useState('');

  const [retentionInput, setRetentionInput] = useState('');
  const [retentionBusy, setRetentionBusy] = useState(false);
  const [retentionMessage, setRetentionMessage] = useState('');

  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState('');

  useEffect(() => {
    if (!visible) return;
    setLoadError('');
    setRetentionMessage('');
    setPasswordMessage('');
    setOldPassword('');
    setNewPassword('');
    fetchProfile()
      .then((data) => {
        setProfile(data);
        setRetentionInput(String(data.completed_items_retention_days));
      })
      .catch(() => setLoadError('Could not load your profile.'));
  }, [visible]);

  const isPremium =
    profile?.plan === 'PR' &&
    profile?.premium_until &&
    new Date(profile.premium_until) >= new Date(new Date().toDateString());

  const handleSaveRetention = async () => {
    const days = parseInt(retentionInput, 10);
    if (!Number.isFinite(days) || days < 1 || days > 31) {
      setRetentionMessage('Enter a number between 1 and 31.');
      return;
    }
    setRetentionBusy(true);
    setRetentionMessage('');
    try {
      const updated = await updateRetentionDays(days);
      setProfile(updated);
      setRetentionMessage('Saved successfully.');
    } catch (err: any) {
      setRetentionMessage(getErrorMessage(err, 'Could not save. Try again.'));
    } finally {
      setRetentionBusy(false);
    }
  };

  const handlePasswordSubmit = async () => {
    const hadPassword = profile.has_password;
    if (!newPassword || (hadPassword && !oldPassword)) {
      setPasswordMessage('Fill in all fields.');
      return;
    }
    setPasswordBusy(true);
    setPasswordMessage('');
    try {
      if (hadPassword) {
        await changePassword(oldPassword, newPassword);
      } else {
        await setPassword(newPassword);
        setProfile({ ...profile, has_password: true });
      }
      setOldPassword('');
      setNewPassword('');
      setPasswordMessage(hadPassword ? 'Password changed.' : 'Password set.');
    } catch (err: any) {
      setPasswordMessage(getErrorMessage(err, 'Could not update password.'));
    } finally {
      setPasswordBusy(false);
    } 
  };

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <LinearGradient colors={[Colors.light.background, '#F8FAFC', '#E2F1F1']} style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerTitleRow}>
              <Ionicons name="person-circle-outline" size={28} color={Colors.light.darkRed} />
              <ThemedText type="title" style={styles.title}>
                Profile
              </ThemedText>
            </View>
            <TouchableOpacity onPress={onClose} style={styles.closeButton} activeOpacity={0.7}>
              <Ionicons name="close-circle" size={30} color={Colors.light.textSecondary} />
            </TouchableOpacity>
          </View>

          <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
            {loadError ? (
              <View style={styles.errorCard}>
                <Ionicons name="alert-circle-outline" size={20} color={Colors.light.danger} />
                <ThemedText style={styles.error}>{loadError}</ThemedText>
              </View>
            ) : null}

            {profile ? (
              <>
                {/* User Avatar Card */}
                <View style={styles.avatarCard}>
                  <View style={styles.avatarCircle}>
                    <ThemedText style={styles.avatarText}>
                      {profile.email ? profile.email.charAt(0).toUpperCase() : 'U'}
                    </ThemedText>
                  </View>
                  <ThemedText style={styles.userEmail}>{profile.email}</ThemedText>
                  <View style={[styles.planBadge, isPremium ? styles.premiumBadge : styles.freeBadge]}>
                    <Ionicons
                      name={isPremium ? 'sparkles' : 'person-outline'}
                      size={14}
                      color={isPremium ? '#047857' : '#475569'}
                    />
                    <ThemedText style={[styles.planBadgeText, isPremium ? styles.premiumText : styles.freeText]}>
                      {isPremium ? `Premium (until ${profile.premium_until})` : 'Free Plan'}
                    </ThemedText>
                  </View>
                </View>

                {/* Data Retention Settings */}
                <Card style={styles.card}>
                  <View style={styles.cardHeader}>
                    <Ionicons name="time-outline" size={20} color={Colors.light.darkRed} />
                    <ThemedText style={styles.cardTitle}>Item Retention</ThemedText>
                  </View>
                  
                  <ThemedText style={styles.sectionSubtitle}>
                    Number of days to keep completed items before auto-deletion.
                  </ThemedText>

                  {isPremium ? (
                    <View style={styles.inputGroup}>
                      <TextInput
                        keyboardType="number-pad"
                        value={retentionInput}
                        onChangeText={setRetentionInput}
                        placeholder="1 - 31 days"
                      />
                      {retentionMessage ? (
                        <ThemedText style={styles.helper}>{retentionMessage}</ThemedText>
                      ) : null}
                      <Button
                        title={retentionBusy ? 'Saving…' : 'Save Retention Days'}
                        onPress={handleSaveRetention}
                        disabled={retentionBusy}
                      />
                    </View>
                  ) : (
                    <View style={styles.disabledRetentionBox}>
                      <Ionicons name="lock-closed-outline" size={16} color={Colors.light.textSecondary} />
                      <ThemedText style={styles.helper}>
                        Currently {profile.completed_items_retention_days} days. Only Premium users can change this setting.
                      </ThemedText>
                    </View>
                  )}
                </Card>

                <Card style={styles.card}>
                      
                  <ThemedText type="small" style={styles.cardTitle}>
                    {profile.has_password ? 'Change password' : 'Set a password'}
                  </ThemedText>

                  {profile.has_password ? (
                    <TextInput
                      placeholder="Current password"
                      secureTextEntry
                      value={oldPassword}
                      onChangeText={setOldPassword}
                    />
                  ) : (
                    <ThemedText style={styles.helper}>
                      You signed in with Google. Set a password if you also want to log in with your email.
                    </ThemedText>
                  )}

                  <TextInput
                    placeholder="New password"
                    secureTextEntry
                    value={newPassword}
                    onChangeText={setNewPassword}
                  />

                  {passwordMessage ? <ThemedText style={styles.helper}>{passwordMessage}</ThemedText> : null}

                  <Button
                    title={passwordBusy ? 'Saving…' : profile.has_password ? 'Change password' : 'Set password'}
                    onPress={handlePasswordSubmit}
                    disabled={passwordBusy}
                  />
                </Card>

                {/* Logout Button */}
                <View style={styles.logoutWrapper}>
                  <Button title="Logout" variant="danger" onPress={logout} />
                </View>
              </>
            ) : null}
          </ScrollView>
        </SafeAreaView>
      </LinearGradient>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safeArea: { flex: 1, paddingHorizontal: Spacing.four },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: Spacing.three,
  },
  headerTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  title: {
    color: Colors.light.darkRed,
    fontSize: 22,
    fontWeight: '700',
  },
  closeButton: {
    padding: 2,
  },
  content: {
    gap: Spacing.three,
    paddingBottom: Spacing.four,
  },
  avatarCard: {
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    padding: Spacing.three,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  avatarCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: Colors.light.darkRed,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.two,
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: 26,
    fontWeight: 'bold',
  },
  userEmail: {
    fontSize: 16,
    fontWeight: '600',
    color: Colors.light.text,
    marginBottom: Spacing.two,
  },
  planBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
  },
  premiumBadge: {
    backgroundColor: '#D1FAE5',
  },
  freeBadge: {
    backgroundColor: '#F1F5F9',
  },
  planBadgeText: {
    fontSize: 13,
    fontWeight: '600',
  },
  premiumText: {
    color: '#047857',
  },
  freeText: {
    color: '#475569',
  },
  card: {
    gap: Spacing.two,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    marginBottom: 4,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: Colors.light.text,
  },
  sectionSubtitle: {
    fontSize: 13,
    color: Colors.light.textSecondary,
    marginBottom: Spacing.two,
  },
  inputGroup: {
    gap: Spacing.two,
  },
  disabledRetentionBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#F8FAFC',
    padding: Spacing.two,
    borderRadius: 8,
  },
  helper: {
    fontSize: 13,
    color: Colors.light.textSecondary,
  },
  errorCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#FEE2E2',
    padding: Spacing.three,
    borderRadius: 8,
  },
  error: {
    color: Colors.light.danger,
    fontSize: 14,
  },
  logoutWrapper: {
    marginTop: Spacing.two,
  },
});