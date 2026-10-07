// src/components/item-detail-modal.tsx
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Linking,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';

import { updateSavedItem, deleteSavedItem } from '@/api/savedItems';
import { fetchCategories } from '@/api/categories';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { TextInput } from '@/components/ui/TextInput';
import { ThemedText } from '@/components/themed-text';
import { CategoryChip } from '@/components/category-chip';
import { Colors, Spacing } from '@/constants/theme';
import { daysUntilPurge } from '@/utils/retention';
import { getErrorMessage } from '@/utils/errors';

interface ItemDetailModalProps {
  item: any | null;
  onClose: () => void;
  onUpdated: (updatedItem: any) => void;
  onDeleted: (id: number) => void;
  retentionDays?: number;
  isPremium?: boolean;
}

export function ItemDetailModal({
  item,
  onClose,
  onUpdated,
  onDeleted,
  retentionDays = 7,
  isPremium = false,
}: ItemDetailModalProps) {
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [allCategories, setAllCategories] = useState<any[]>([]);
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<number[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (item) {
      setName(item.name || '');
      const existingCategoryIds = item.categories
        ? item.categories.map((c: any) => c.category || c.id)
        : [];
      setSelectedCategoryIds(existingCategoryIds);

      fetchCategories()
        .then(setAllCategories)
        .catch(() => {});
    }
  }, [item]);

  if (!item) return null;

  const imageUrl = item.metadata?.image || item.image_url;
  const isDone = item.status === 'completed';
  const daysLeft = isDone ? daysUntilPurge(item.completed_at, retentionDays) : null;

  const toggleCategory = (id: number) => {
    setSelectedCategoryIds((prev) =>
      prev.includes(id) ? prev.filter((catId) => catId !== id) : [...prev, id]
    );
  };

  const handleOpenLink = () => {
    if (item.url) {
      Linking.openURL(item.url).catch(() => {});
    }
  };
  
  const handleStatusToggle = async () => {
      try {
        setSaving(true);
        setError('');
        const newStatus = isDone ? 'to_do' : 'completed';
        
        const payload: any = {
          name: name.trim(),
          status: newStatus,
          categories: selectedCategoryIds.map((id, index) => ({
            category: id,
            priority: index + 1,
          })),
        };

        const updated = await updateSavedItem(item.id, payload);
        onUpdated(updated);
        onClose(); 
      } catch (err: any) {
        setError(getErrorMessage(err, 'Could not save changes.'));
      } finally {
        setSaving(false);
      }
    };

  const handleSave = async () => {
    try {
      setSaving(true);
      const payload: any = {
        name: name.trim(),
        categories: selectedCategoryIds.map((id, index) => ({
          category: id,
          priority: index + 1,
        })),
      };

      const updated = await updateSavedItem(item.id, payload);
      onUpdated(updated);
      onClose();
    } catch (err: any) {
      setError(getErrorMessage(err, 'Could not save changes.'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      setDeleting(true);
      await deleteSavedItem(item.id);
      onDeleted(item.id);
      onClose();
    } catch (err: any) {
      setError(getErrorMessage(err, 'Could not delete item.'));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Modal visible={!!item} animationType="slide" onRequestClose={onClose}>
      <LinearGradient colors={Colors.light.gradientBackground} style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerTitleRow}>
              <Ionicons name="document-text-outline" size={26} color={Colors.light.darkRed} />
              <ThemedText type="title" style={styles.titleText}>
                Item Details
              </ThemedText>
            </View>
            <TouchableOpacity onPress={onClose} style={styles.closeButton} activeOpacity={0.7}>
              <Ionicons name="close-circle" size={30} color={Colors.light.textSecondary} />
            </TouchableOpacity>
          </View>

          <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
            {/* Media / Image Preview Card */}
            {imageUrl ? (
              <View style={styles.imageContainer}>
                <Image
                  source={{ uri: imageUrl }}
                  style={styles.itemImage}
                  resizeMode="cover"
                />
                <View style={[styles.statusBadge, isDone ? styles.doneBadge : styles.todoBadge]}>
                  <Ionicons
                    name={isDone ? 'checkmark-circle' : 'time-outline'}
                    size={14}
                    color={isDone ? '#047857' : '#0284C7'}
                  />
                  <ThemedText style={[styles.statusBadgeText, isDone ? styles.doneText : styles.todoText]}>
                    {isDone ? 'Completed' : 'To Do'}
                  </ThemedText>
                </View>
              </View>
            ) : null}

            <Card style={styles.card}>
              {/* Title / Label Input */}
              <View style={styles.fieldGroup}>
                <View style={styles.fieldHeader}>
                  <Ionicons name="create-outline" size={18} color="#636366" />
                  <ThemedText style={styles.label}>Title / Name</ThemedText>
                </View>
                <TextInput
                  value={name}
                  onChangeText={setName}
                  placeholder="Article title or custom note..."
                />
              </View>

              {/* URL Section */}
              {item.url ? (
                <View style={styles.fieldGroup}>
                  <View style={styles.fieldHeader}>
                    <Ionicons name="link-outline" size={18} color="#636366" />
                    <ThemedText style={styles.label}>URL Link</ThemedText>
                  </View>
                  <Pressable style={styles.urlBox} onPress={handleOpenLink}>
                    <ThemedText style={styles.urlText} numberOfLines={2}>
                      {item.url}
                    </ThemedText>
                    <Ionicons name="open-outline" size={16} color="#007AFF" />
                  </Pressable>
                </View>
              ) : null}

              {/* Categories Section */}
              <View style={styles.fieldGroup}>
                <View style={styles.fieldHeader}>
                  <Ionicons name="pricetags-outline" size={18} color="#636366" />
                  <ThemedText style={styles.label}>Categories</ThemedText>
                </View>
                <View style={styles.categoryContainer}>
                  {allCategories.map((cat) => {
                    const isSelected = selectedCategoryIds.includes(cat.id);
                    return (
                      <CategoryChip
                        key={cat.id}
                        label={cat.name}
                        color={cat.color}
                        selected={isSelected}
                        onPress={() => toggleCategory(cat.id)}
                      />
                    );
                  })}
                </View>
              </View>
              
              {isDone && daysLeft !== null && (
                <View style={styles.fieldGroup}>
                  <View style={styles.fieldHeader}>
                    <Ionicons name="trash-outline" size={18} color="#636366" />
                    <ThemedText style={styles.label}>Retention</ThemedText>
                  </View>
                  <ThemedText style={styles.retentionNote}>
                    {daysLeft <= 0
                      ? 'This item will be deleted soon.'
                      : `This item will be permanently deleted in ${daysLeft} day${daysLeft === 1 ? '' : 's'}.`}
                  </ThemedText>
                  {!isPremium && (
                    <ThemedText style={styles.upgradeNote}>
                      You can extend this by upgrading to Premium.
                    </ThemedText>
                  )}
                </View>
              )}

              {/* Error Alert */}
              {error ? (
                <View style={styles.errorCard}>
                  <Ionicons name="alert-circle-outline" size={18} color={Colors.light.danger} />
                  <ThemedText style={styles.error}>{error}</ThemedText>
                </View>
              ) : null}
            </Card>

            {/* Action Buttons Group */}
            <View style={styles.actions}>
              <View style={styles.primaryActions}>
                <Button
                  title={isDone ? 'Mark as To Do' : 'Mark as Done'}
                  variant="secondary"
                  onPress={handleStatusToggle}
                  disabled={saving || deleting}
                  style={styles.actionBtn}
                />
                <Button
                  title="Save Changes"
                  onPress={handleSave}
                  disabled={saving || deleting}
                  style={styles.actionBtn}
                />
              </View>

              <Button
                title="Delete Item"
                variant="danger"
                onPress={handleDelete}
                disabled={saving || deleting}
              />
            </View>

            {(saving || deleting) && (
              <ActivityIndicator style={styles.loader} color="#007AFF" />
            )}
          </ScrollView>
        </SafeAreaView>
      </LinearGradient>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  safeArea: {
    flex: 1,
    paddingHorizontal: Spacing.four,
  },
  content: {
    paddingBottom: Spacing.four,
    gap: Spacing.three,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: Spacing.three,
  },
  headerTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  titleText: {
    fontSize: 22,
    fontWeight: '700',
    color: Colors.light.darkRed,
  },
  closeButton: {
    padding: 2,
  },
  imageContainer: {
    width: '100%',
    height: 190,
    borderRadius: 18,
    overflow: 'hidden',
    backgroundColor: '#E5E5EA',
    position: 'relative',
  },
  itemImage: {
    width: '100%',
    height: '100%',
  },
  statusBadge: {
    position: 'absolute',
    top: 12,
    right: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
  },
  doneBadge: {
    backgroundColor: 'rgba(209, 250, 229, 0.95)',
  },
  todoBadge: {
    backgroundColor: 'rgba(224, 242, 254, 0.95)',
  },
  statusBadgeText: {
    fontSize: 12,
    fontWeight: '600',
  },
  doneText: {
    color: '#047857',
  },
  todoText: {
    color: '#0284C7',
  },
  card: {
    gap: Spacing.three,
    padding: Spacing.three,
  },
  fieldGroup: {
    gap: 6,
  },
  fieldHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#3A3A3C',
  },
  urlBox: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(0, 122, 255, 0.06)',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 10,
    gap: 8,
  },
  urlText: {
    flex: 1,
    fontSize: 14,
    color: '#007AFF',
    fontWeight: '500',
  },
  categoryContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    marginTop: 4,
  },
  actions: {
    gap: Spacing.two,
    marginTop: Spacing.one,
  },
  primaryActions: {
    flexDirection: 'row',
    gap: Spacing.two,
  },
  actionBtn: {
    flex: 1,
  },
  loader: {
    marginVertical: Spacing.two,
  },
  errorCard: {
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
  },
  retentionNote: { 
    fontSize: 13, 
    color: '#3A3A3C' 
  },
  upgradeNote: { 
    fontSize: 12, 
    color: Colors.light.primary, 
    fontStyle: 'italic', 
    marginTop: 2 
  },
});