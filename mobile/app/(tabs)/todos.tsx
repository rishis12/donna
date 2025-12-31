import { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TextInput,
  TouchableOpacity,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAppStore } from '../../stores/appStore';

// Earthy tan/brown colors
const colors = {
  background: '#FAF8F5',
  surface: '#FFFFFF',
  surfaceAlt: '#F5F0E8',
  primary: '#B89460',
  primaryLight: '#F7F3EE',
  text: '#443D35',
  textMuted: '#9C8B78',
  textLight: '#B8A690',
  border: '#E8DFD3',
  success: '#8B9A6F',
  successLight: '#EDF2E7',
};

export default function TodosScreen() {
  const { todos, addTodo, toggleTodo, removeTodo } = useAppStore();
  const [newTodoText, setNewTodoText] = useState('');

  const handleAddTodo = () => {
    if (!newTodoText.trim()) return;
    addTodo(newTodoText.trim());
    setNewTodoText('');
  };

  const incompleteTodos = todos.filter((t) => !t.completed);
  const completedTodos = todos.filter((t) => t.completed);

  const renderTodo = ({ item }: { item: typeof todos[0] }) => (
    <View style={styles.todoItem}>
      <TouchableOpacity
        style={[styles.checkbox, item.completed && styles.checkboxChecked]}
        onPress={() => toggleTodo(item.id)}
      >
        {item.completed && <Ionicons name="checkmark" size={16} color="#fff" />}
      </TouchableOpacity>
      <Text style={[styles.todoText, item.completed && styles.todoTextCompleted]}>
        {item.text}
      </Text>
      <TouchableOpacity style={styles.deleteButton} onPress={() => removeTodo(item.id)}>
        <Ionicons name="close" size={18} color={colors.textMuted} />
      </TouchableOpacity>
    </View>
  );

  return (
    <View style={styles.container}>
      {/* Add Todo Input */}
      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          placeholder="Add a new task..."
          placeholderTextColor={colors.textMuted}
          value={newTodoText}
          onChangeText={setNewTodoText}
          onSubmitEditing={handleAddTodo}
          returnKeyType="done"
        />
        <TouchableOpacity
          style={[styles.addButton, !newTodoText.trim() && styles.addButtonDisabled]}
          onPress={handleAddTodo}
          disabled={!newTodoText.trim()}
        >
          <Ionicons name="add" size={24} color="#fff" />
        </TouchableOpacity>
      </View>

      {/* Todo List */}
      <FlatList
        data={[...incompleteTodos, ...completedTodos]}
        keyExtractor={(item) => item.id}
        renderItem={renderTodo}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <View style={styles.emptyIcon}>
              <Text style={styles.emptyEmoji}>✓</Text>
            </View>
            <Text style={styles.emptyTitle}>All caught up!</Text>
            <Text style={styles.emptyText}>Add tasks to keep track of your to-dos</Text>
          </View>
        }
        ListHeaderComponent={
          incompleteTodos.length > 0 ? (
            <Text style={styles.sectionHeader}>
              {incompleteTodos.length} task{incompleteTodos.length !== 1 ? 's' : ''} remaining
            </Text>
          ) : null
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 16,
    gap: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.background,
  },
  input: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    color: colors.text,
    borderWidth: 1,
    borderColor: colors.border,
  },
  addButton: {
    width: 52,
    height: 52,
    borderRadius: 14,
    backgroundColor: colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  addButtonDisabled: {
    backgroundColor: colors.border,
  },
  listContent: {
    padding: 16,
    paddingBottom: 40,
  },
  sectionHeader: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textMuted,
    marginBottom: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  todoItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: colors.border,
    marginRight: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxChecked: {
    backgroundColor: colors.success,
    borderColor: colors.success,
  },
  todoText: {
    flex: 1,
    fontSize: 16,
    color: colors.text,
  },
  todoTextCompleted: {
    color: colors.textMuted,
    textDecorationLine: 'line-through',
  },
  deleteButton: {
    padding: 4,
    marginLeft: 8,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
    marginTop: 60,
  },
  emptyIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.successLight,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  emptyEmoji: {
    fontSize: 36,
    color: colors.success,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 8,
    fontFamily: Platform.OS === 'ios' ? 'Georgia' : 'serif',
  },
  emptyText: {
    fontSize: 15,
    color: colors.textMuted,
    textAlign: 'center',
    lineHeight: 22,
  },
});

