import { PropsWithChildren } from 'react';
import { StyleSheet, View, ViewStyle } from 'react-native';

import { Colors, Spacing } from '@/constants/theme';

type Props = PropsWithChildren<{
  style?: ViewStyle;
  variant?: 'default' | 'glass';
}>;

export function Card({
  children,
  style,
  variant = 'default',
}: Props) {
  return (
    <View
      style={[
        styles.base,
        styles[variant],
        style,
      ]}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: 20,
    padding: Spacing.four,
    gap: Spacing.two,

    borderWidth: 1,
    borderColor: Colors.light.border,

    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.08,
    shadowRadius: 8,

    elevation: 3,
  },

  default: {
    backgroundColor: Colors.light.backgroundElement,
  },

  glass: {
    backgroundColor: 'rgba(255,255,255,0.92)',
  },
});