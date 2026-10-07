import { TextInput as RNTextInput, StyleSheet, TextInputProps } from 'react-native';

import { Colors, Spacing } from '@/constants/theme';

type Props = TextInputProps & {
  error?: boolean;
};

export function TextInput({ error = false, style, ...props }: Props) {
  return (
    <RNTextInput
      style={[
        styles.input,
        error && styles.error,
        style,
      ]}
      placeholderTextColor={Colors.light.textSecondary}
      {...props}
    />
  );
}

const styles = StyleSheet.create({
  input: {
    height: 52,
    borderWidth: 1,
    borderColor: Colors.light.border,
    borderRadius: 14,
    paddingHorizontal: Spacing.three,

    backgroundColor: Colors.light.backgroundElement,
    color: Colors.light.text,

    fontFamily: 'Inter',
    fontSize: 16,
  },

  error: {
    borderColor: Colors.light.danger,
  },
});