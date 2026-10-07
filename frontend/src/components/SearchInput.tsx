import React from 'react';
import { View, TextInput, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface SearchInputProps {
  value: string;
  onChangeText: (text: string) => void;
  onClear?: () => void;
  placeholder?: string;
}

export const SearchInput: React.FC<SearchInputProps> = ({
  value,
  onChangeText,
  onClear,
  placeholder = 'جستجو در عنوان، لینک یا منبع...',
}) => {
  return (
    <View style={styles.container}>
      <Ionicons name="search-outline" size={20} color="#8E8E93" style={styles.icon} />
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor="#8E8E93"
        returnKeyType="search"
        clearButtonMode="while-editing" // مخصوص iOS
        autoCorrect={false}
      />
      {value.length > 0 && (
        <TouchableOpacity onPress={onClear || (() => onChangeText(''))} style={styles.clearButton}>
          <Ionicons name="close-circle" size={18} color="#8E8E93" />
        </TouchableOpacity>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F2F2F7',
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 8,
    marginHorizontal: 16,
    marginVertical: 8,
  },
  icon: {
    marginRight: 6,
  },
  input: {
    flex: 1,
    fontSize: 15,
    color: '#000000',
    textAlign: 'right', // در صورت نیاز به پشتیبانی راست‌چین
  },
  clearButton: {
    padding: 2,
  },
});
