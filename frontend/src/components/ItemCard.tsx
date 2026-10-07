import React from 'react';
import { View, StyleSheet, Image, Pressable } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { Ionicons } from '@expo/vector-icons';
import { daysUntilPurge } from '@/utils/retention';

interface ItemCardProps {
  item: any;
  onPress: () => void;
  retentionDays?: number;
}

export function ItemCard({ item, onPress, retentionDays = 7 }: ItemCardProps) {  const imageUrl = item.metadata?.image || item.image_url;
  const title = item.metadata?.title || item.name || item.url;
  const source = item.source;
  const isDone = item.status === 'completed';
  const daysLeft = isDone ? daysUntilPurge(item.completed_at, retentionDays) : null;
  const isProcessing =
    item.extraction_status === 'pending' || item.extraction_status === 'processing';

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
    >
      {imageUrl ? (
        <View style={styles.imageWrapper}>
          <Image source={{ uri: imageUrl }} style={styles.image} resizeMode="cover" />
        </View>
      ) : null}

      <View style={styles.body}>
        <ThemedText style={styles.title} numberOfLines={2}>
          {title}
        </ThemedText>

        <View style={styles.footer}>
          {source ? (
            <View style={styles.badge}>
              <Ionicons name="link-outline" size={12} color="#636366" />
              <ThemedText style={styles.badgeText}>{source}</ThemedText>
            </View>
          ) : null}

          {isProcessing && (
            <View style={[styles.badge, styles.processingBadge]}>
              <ThemedText style={styles.processingText}>Fetching...</ThemedText>
            </View>
          )}

          {isDone && daysLeft !== null && (
            <View style={[styles.badge, styles.retentionBadge]}>
              <Ionicons name="trash-outline" size={12} color="#8E8E93" />
              <ThemedText style={styles.retentionText}>
                {daysLeft <= 0 ? 'Deleting soon' : `Deletes in ${daysLeft}d`}
              </ThemedText>
            </View>
          )}
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#EFEFF4',
    overflow: 'hidden',
    marginBottom: Spacing.three,
    // Subtle Box Shadow
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.03,
    shadowRadius: 10,
    elevation: 2,
  },
  pressed: {
    opacity: 0.88,
    transform: [{ scale: 0.995 }],
  },
  imageWrapper: {
    width: '100%',
    height: 150,
    backgroundColor: '#F2F2F7',
  },
  image: {
    width: '100%',
    height: '100%',
  },
  body: {
    padding: Spacing.three,
    gap: Spacing.two,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1C1C1E',
    lineHeight: 22,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    marginTop: 2,
  },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#F2F2F7',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: '500',
    color: '#636366',
  },
  processingBadge: {
    backgroundColor: '#E5F1FF',
  },
  processingText: {
    fontSize: 12,
    fontWeight: '500',
    color: '#007AFF',
  },
  retentionBadge: {
    backgroundColor: '#FFF4E5'
  },

  retentionText: { 
    fontSize: 12, 
    fontWeight: '500', 
    color: '#B45309'
  },
});