import { useEffect, useState } from 'react';
import { Modal, ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';

import { fetchCategories } from '@/api/categories';
import { createSavedItem } from '@/api/savedItems';
import { CategoryChip } from '@/components/category-chip';
import { ThemedText } from '@/components/themed-text';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { TextInput } from '@/components/ui/TextInput';
import { Colors, Spacing } from '@/constants/theme';
import { getErrorMessage } from '@/utils/errors';

type Props = {
  visible: boolean;
  onClose: () => void;
  onCreated: () => void;
  initialUrl?: string;
  initialName?: string;
};

export function AddItemModal({ visible, onClose, onCreated, initialUrl = '', initialName = '' }: Props) {
  const [name, setName] = useState(initialName);
  const [url, setUrl] = useState(initialUrl);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [categories, setCategories] = useState<any[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  useEffect(() => {
    if (visible) {
      fetchCategories().then(setCategories).catch(() => {});
    }
  }, [visible]);

  useEffect(() => {
  if (visible) {
    setName(initialName);
    setUrl(initialUrl);
  }
  }, [visible, initialName, initialUrl]);

  const reset = () => {
    setName('');
    setUrl('');
    setError('');
    setSelectedIds([]);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const toggleCategory = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    );
  };

  const handleSubmit = async () => {
    const trimmedName = name.trim();
    const trimmedUrl = url.trim();

    if (!trimmedName && !trimmedUrl) {
      setError('Please enter a name or a link.');
      return;
    }

    setSubmitting(true);
    setError('');
    try {
      await createSavedItem({ name: trimmedName, url: trimmedUrl, categoryIds: selectedIds });
      reset();
      onCreated();
      onClose();
    // } catch (err: any) {
    //   setError(getErrorMessage(err, 'Could not save the item. Try again.'));
    // } finally {
    } catch (err: any) {
      console.log('SAVE ITEM STATUS:', err?.response?.status);
      console.log('SAVE ITEM DATA:', err?.response?.data);

      setError(getErrorMessage(err, 'Could not save the item. Try again.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={handleClose}>
      <LinearGradient colors={Colors.light.gradientBackground} style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerTitleRow}>
              <Ionicons name="add-circle-outline" size={28} color={Colors.light.darkRed} />
              <ThemedText type="title" style={styles.title}>
                Add New Item
              </ThemedText>
            </View>
            <TouchableOpacity onPress={handleClose} style={styles.closeButton} activeOpacity={0.7}>
              <Ionicons name="close-circle" size={30} color={Colors.light.textSecondary} />
            </TouchableOpacity>
          </View>

          <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
            <Card style={styles.card}>
              {/* URL Input Box */}
              <View style={styles.inputFieldContainer}>
                <View style={styles.fieldHeader}>
                  <Ionicons name="link-outline" size={18} color="#636366" />
                  <ThemedText style={styles.fieldLabel}>URL or Link</ThemedText>
                </View>
                <TextInput
                  placeholder="https://example.com/article"
                  value={url}
                  onChangeText={setUrl}
                  autoCapitalize="none"
                  autoCorrect={false}
                  keyboardType="url"
                />
              </View>

              {/* Title / Name Input Box */}
              <View style={styles.inputFieldContainer}>
                <View style={styles.fieldHeader}>
                  <Ionicons name="bookmark-outline" size={18} color="#636366" />
                  <ThemedText style={styles.fieldLabel}>Title or Note (Optional)</ThemedText>
                </View>
                <TextInput
                  placeholder="My saved article title..."
                  value={name}
                  onChangeText={setName}
                />
              </View>

              {/* Categories Section */}
              {categories.length > 0 ? (
                <View style={styles.categoriesSection}>
                  <View style={styles.fieldHeader}>
                    <Ionicons name="pricetags-outline" size={18} color="#636366" />
                    <ThemedText style={styles.fieldLabel}>Categories</ThemedText>
                  </View>
                  <View style={styles.chipRow}>
                    {categories.map((cat) => (
                      <CategoryChip
                        key={cat.id}
                        label={cat.name}
                        color={cat.color}
                        selected={selectedIds.includes(cat.id)}
                        onPress={() => toggleCategory(cat.id)}
                      />
                    ))}
                  </View>
                </View>
              ) : null}

              {/* Error Message */}
              {error ? (
                <View style={styles.errorContainer}>
                  <Ionicons name="alert-circle-outline" size={18} color={Colors.light.danger} />
                  <ThemedText style={styles.error}>{error}</ThemedText>
                </View>
              ) : null}

              {/* Action Buttons */}
              <View style={styles.buttons}>
                <Button
                  title="Cancel"
                  variant="secondary"
                  onPress={handleClose}
                  disabled={submitting}
                  style={styles.actionBtn}
                />
                <Button
                  title={submitting ? 'Saving…' : 'Save Item'}
                  onPress={handleSubmit}
                  disabled={submitting}
                  style={styles.actionBtn}
                />
              </View>
            </Card>
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
    paddingBottom: Spacing.four,
  },
  card: {
    gap: Spacing.three,
    padding: Spacing.three,
  },
  inputFieldContainer: {
    gap: 6,
  },
  fieldHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  fieldLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#3A3A3C',
  },
  categoriesSection: {
    gap: 8,
    marginTop: 4,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    marginTop: 4,
  },
  buttons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: Spacing.two,
    gap: Spacing.two,
  },
  actionBtn: {
    flex: 1,
  },
  errorContainer: {
    paddingHorizontal: 12,
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#FEE2E2',
    padding: Spacing.two,
    borderRadius: 8,
  },
  error: {
    color: Colors.light.danger,
    fontSize: 13,
    lineHeight: 20,
    flexShrink: 1,
  },
});