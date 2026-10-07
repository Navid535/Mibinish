import { useCallback, useEffect, useState } from 'react';
import { FlatList, Modal, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';

import { createCategory, deleteCategory, fetchCategories } from '@/api/categories';
import { ThemedText } from '@/components/themed-text';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { TextInput } from '@/components/ui/TextInput';
import { CATEGORY_COLORS, ColorSwatchPicker } from '@/components/ui/ColorSwatchPicker';
import { Colors, Spacing } from '@/constants/theme';
import { getErrorMessage } from '@/utils/errors';

type Props = {
  visible: boolean;
  onClose: () => void;
  onChanged: () => void;
};

export function ManageCategoriesModal({ visible, onClose, onChanged }: Props) {
  const [categories, setCategories] = useState<any[]>([]);
  const [name, setName] = useState('');
  const [color, setColor] = useState(CATEGORY_COLORS[0]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await fetchCategories();
      setCategories(data);
    } catch {
      setError('Could not load categories.');
    }
  }, []);

  useEffect(() => {
    if (visible) load();
  }, [visible, load]);

  const handleCreate = async () => {
    const trimmed = name.trim();
    if (!trimmed) return;

    setBusy(true);
    setError('');
    try {
      await createCategory({ name: trimmed, color });
      setName('');
      setColor(CATEGORY_COLORS[0]);
      await load();
      onChanged();
    } catch (err: any) {
      setError(getErrorMessage(err, 'Could not create category.'));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (id: number) => {
    setBusy(true);
    try {
      await deleteCategory(id);
      await load();
      onChanged();
    } catch (err: any) {
      setError(getErrorMessage(err, 'Could not delete category.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <LinearGradient colors={[Colors.light.background, '#FFFFFF', '#D9F3F2']} style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <ThemedText type="title" style={styles.title}>
            Categories
          </ThemedText>

          <Card>
            <View style={styles.row}>
              <TextInput
                style={styles.input}
                placeholder="New category name"
                value={name}
                onChangeText={setName}
              />
              <Button title="Add" onPress={handleCreate} disabled={busy} />
            </View>

            <ColorSwatchPicker value={color} onChange={setColor} />

            {error ? <ThemedText style={styles.error}>{error}</ThemedText> : null}
          </Card>

          <FlatList
            data={categories}
            keyExtractor={(item) => String(item.id)}
            contentContainerStyle={styles.list}
            ListEmptyComponent={
              <ThemedText style={styles.empty}>No categories yet.</ThemedText>
            }
            renderItem={({ item }) => (
              <Card style={styles.categoryRow}>
                <View style={styles.categoryInfo}>
                  <View style={[styles.dot, { backgroundColor: item.color }]} />
                  <ThemedText style={styles.categoryName}>{item.name}</ThemedText>
                </View>
                <Button
                  title="Delete"
                  variant="danger"
                  onPress={() => handleDelete(item.id)}
                  disabled={busy}
                />
              </Card>
            )}
          />

          <Button title="Close" variant="secondary" onPress={onClose} />
        </SafeAreaView>
      </LinearGradient>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safeArea: { flex: 1, padding: Spacing.four, gap: Spacing.three },
  title: { color: Colors.light.darkRed },
  row: { flexDirection: 'row', gap: Spacing.two, alignItems: 'center' },
  input: { flex: 1 },
  list: { gap: Spacing.two, paddingVertical: Spacing.two },
  categoryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  categoryInfo: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  dot: { width: 16, height: 16, borderRadius: 8 },
  categoryName: { fontFamily: 'InterSemiBold', fontSize: 16, color: Colors.light.text },
  error: { color: Colors.light.danger },
  empty: { textAlign: 'center', color: Colors.light.textSecondary, marginTop: Spacing.four },
});