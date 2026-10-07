import { Pressable, StyleSheet, View } from 'react-native';

import { Spacing } from '@/constants/theme';

export const CATEGORY_COLORS = [
  '#3299a8', // پیش‌فرض مدل
  '#E07A5F',
  '#81B29A',
  '#F2CC8F',
  '#6C63FF',
  '#EF476F',
  '#118AB2',
  '#8D6A9F',
];

type Props = {
  value: string;
  onChange: (color: string) => void;
};

export function ColorSwatchPicker({ value, onChange }: Props) {
  return (
    <View style={styles.row}>
      {CATEGORY_COLORS.map((color) => (
        <Pressable
          key={color}
          onPress={() => onChange(color)}
          style={[
            styles.swatch,
            { backgroundColor: color },
            value === color && styles.selected,
          ]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  swatch: {
    width: 32,
    height: 32,
    borderRadius: 16,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  selected: {
    borderColor: '#000000',
  },
});