import '@/global.css';

import { Platform } from 'react-native';

export const Colors = {
  light: {
    text: '#0F172A',              // Slate 900 (خوانایی عالی)
    background: '#F8FAFC',        // Slate 50 (تمیز و خنک)
    backgroundElement: '#FFFFFF', // کارت‌های کاملاً سفید
    backgroundSelected: '#E2E8F0',// Slate 200
    textSecondary: '#64748B',     // Slate 500

    primary: '#0EA5E9',           // Vivid Modern Cyan/Blue
    primaryText: '#FFFFFF',
    danger: '#EF4444',            // Red 500
    darkRed: '#991B1B',           // Slate Dark Red
    border: '#E2E8F0',            // Soft Border

    // گرادیان‌های مدرن تم Light
    gradientBackground: ['#F0F9FF', '#F8FAFC', '#E0F2FE'] as const,
    gradientCard: ['#FFFFFF', '#F8FAFC'] as const,
    gradientPrimary: ['#0EA5E9', '#2563EB'] as const,
  },
  dark: {
    text: '#F8FAFC',
    background: '#0F172A',        // Slate 900 (تاریک عمیق و مدرن)
    backgroundElement: '#1E293B', // Slate 800
    backgroundSelected: '#334155',// Slate 700
    textSecondary: '#94A3B8',     // Slate 400

    primary: '#38BDF8',           // Sky 400
    primaryText: '#0F172A',
    danger: '#F87171',            // Red 400
    darkRed: '#FECACA',
    border: '#334155',

    // گرادیان‌های مدرن تم Dark
    gradientBackground: ['#0F172A', '#1E293B', '#0F172A'] as const,
    gradientCard: ['#1E293B', '#0F172A'] as const,
    gradientPrimary: ['#38BDF8', '#818CF8'] as const,
  },
} as const;

export type ThemeColor = keyof typeof Colors.light & keyof typeof Colors.dark;

export const Fonts = Platform.select({
  ios: {
    sans: 'Inter',
    serif: 'ui-serif',
    rounded: 'ui-rounded',
    mono: 'ui-monospace',
  },
  default: {
    sans: 'Inter',
    serif: 'serif',
    rounded: 'normal',
    mono: 'monospace',
  },
  web: {
    sans: 'Inter',
    serif: 'serif',
    rounded: 'Inter',
    mono: 'monospace',
  },
});

export const Spacing = {
  half: 2,
  one: 4,
  two: 8,
  three: 16,
  four: 24,
  five: 32,
  six: 64,
} as const;

export const BottomTabInset = Platform.select({ ios: 50, android: 80 }) ?? 0;
export const MaxContentWidth = 800;