import { Pressable, StyleSheet } from 'react-native';
import { Colors, Spacing } from '@/constants/theme';
import { ThemedText } from '@/components/themed-text';

type Props = {
  label: string;
  color?: string;
  selected?: boolean;
  onPress?: () => void;
};

export function CategoryChip({
  label,
  color,
  selected = false,
  onPress,
}: Props) {
  const baseColor = color ?? Colors.light.primary;

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.chip,
        selected
          ? { backgroundColor: baseColor, borderColor: baseColor }
          : { backgroundColor: 'rgba(118, 118, 128, 0.08)', borderColor: 'transparent' },
        pressed && styles.pressed,
      ]}
    >
      <ThemedText
        style={[
          styles.text,
          {
            color: selected ? '#FFFFFF' : '#3A3A3C',
            fontWeight: selected ? '600' : '500',
          },
        ]}
      >
        {label}
      </ThemedText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 4,
    borderRadius: 20,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: {
    opacity: 0.75,
    transform: [{ scale: 0.97 }],
  },
  text: {
    fontSize: 13,
    letterSpacing: -0.2,
  },
});