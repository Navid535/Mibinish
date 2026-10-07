import { Platform, StyleSheet, Text, type TextProps } from 'react-native';

import { Colors, Fonts, ThemeColor } from '@/constants/theme';

export type ThemedTextProps = TextProps & {
  type?: 
    | 'default'
    | 'title'
    | 'small'
    | 'smallBold'
    | 'subtitle'
    | 'link'
    | 'linkPrimary'
    | 'code';

  themeColor?: ThemeColor;
};


export function ThemedText({
  style,
  type = 'default',
  themeColor,
  ...rest
}: ThemedTextProps) {

  return (
    <Text
      style={[
        {
          color: Colors.light[themeColor ?? 'text'],
          fontFamily: Fonts.sans,
        },

        type === 'default' && styles.default,
        type === 'title' && styles.title,
        type === 'small' && styles.small,
        type === 'smallBold' && styles.smallBold,
        type === 'subtitle' && styles.subtitle,
        type === 'link' && styles.link,
        type === 'linkPrimary' && styles.linkPrimary,
        type === 'code' && styles.code,

        style,
      ]}
      {...rest}
    />
  );
}


const styles = StyleSheet.create({

  default: {
    fontSize: 16,
    lineHeight: 24,
    fontWeight: '500',
  },

  title: {
    fontSize: 32,
    lineHeight: 38,
    fontWeight: '600',
  },

  subtitle: {
    fontSize: 24,
    lineHeight: 32,
    fontWeight: '600',
  },

  small: {
    fontSize: 14,
    lineHeight: 20,
    fontWeight: '400',
  },

  smallBold: {
    fontSize: 14,
    lineHeight: 20,
    fontWeight: '700',
  },

  link: {
    fontSize: 14,
    lineHeight: 22,
    color: Colors.light.primary,
  },

  linkPrimary: {
    fontSize: 14,
    lineHeight: 22,
    color: Colors.light.primary,
    fontWeight: '600',
  },

  code: {
    fontFamily: Fonts.mono,
    fontSize: 12,
    fontWeight: Platform.select({
      android: '700',
      default: '500',
    }),
  },

});