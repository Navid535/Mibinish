import {
  Pressable,
  StyleSheet,
  Text,
  ViewStyle,
} from 'react-native';

import { Colors, Spacing } from '@/constants/theme';

type ButtonProps = {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  disabled?: boolean;
  style?: ViewStyle;
};

export function Button({
  title,
  onPress,
  variant = 'primary',
  disabled = false,
  style,
}: ButtonProps) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.base,
        styles[variant],
        pressed && styles.pressed,
        disabled && styles.disabled,
        style,
      ]}
    >
      <Text style={[styles.text, styles[`${variant}Text`]]}>
        {title}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    height: 48,
    paddingHorizontal: Spacing.four,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },

  primary: {
    backgroundColor: Colors.light.primary,
  },

  secondary: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: Colors.light.primary,
  },

  danger: {
    backgroundColor: Colors.light.danger,
  },

  ghost: {
    backgroundColor: 'transparent',
  },

  text: {
    fontFamily: 'InterSemiBold',
    fontSize: 16,
  },

  primaryText: {
    color: Colors.light.primaryText,
  },

  secondaryText: {
    color: Colors.light.primary,
  },

  dangerText: {
    color: '#FFFFFF',
  },

  ghostText: {
    color: Colors.light.darkRed,
  },

  pressed: {
    opacity: 0.75,
  },

  disabled: {
    opacity: 0.5,
  },
});