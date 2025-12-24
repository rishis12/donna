import { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAppStore } from '../../stores/appStore';

export default function ChatScreen() {
  const [input, setInput] = useState('');
  const flatListRef = useRef<FlatList>(null);
  const { messages, isLoading, sendMessage, confirmAction, clearHistory } = useAppStore();

  useEffect(() => {
    // Scroll to bottom when messages change
    setTimeout(() => {
      flatListRef.current?.scrollToEnd({ animated: true });
    }, 100);
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const text = input.trim();
    setInput('');
    await sendMessage(text);
  };

  const getIntentIcon = (intent?: string) => {
    switch (intent) {
      case 'schedule_event':
      case 'move_event':
        return 'calendar';
      case 'create_reminder':
        return 'notifications';
      case 'draft_email':
      case 'send_email':
        return 'mail';
      default:
        return null;
    }
  };

  const renderMessage = ({ item }: { item: typeof messages[0] }) => {
    const isUser = item.role === 'user';
    const intentIcon = getIntentIcon(item.intent);

    return (
      <View style={[styles.messageRow, isUser && styles.messageRowUser]}>
        <View
          style={[
            styles.messageBubble,
            isUser ? styles.userBubble : styles.assistantBubble,
          ]}
        >
          {intentIcon && (
            <View style={styles.intentBadge}>
              <Ionicons name={intentIcon as any} size={12} color="#f59e0b" />
              <Text style={styles.intentText}>
                {item.intent?.replace('_', ' ')}
              </Text>
            </View>
          )}
          <Text style={[styles.messageText, isUser && styles.userText]}>
            {item.content}
          </Text>

          {item.requiresConfirmation && item.actionId && (
            <View style={styles.confirmButtons}>
              <TouchableOpacity
                style={styles.confirmButton}
                onPress={() => confirmAction(item.actionId!, true)}
              >
                <Ionicons name="checkmark" size={16} color="#22c55e" />
                <Text style={styles.confirmText}>Do it</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.cancelButton}
                onPress={() => confirmAction(item.actionId!, false)}
              >
                <Ionicons name="close" size={16} color="#888" />
                <Text style={styles.cancelText}>Cancel</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      </View>
    );
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      {/* Header Actions */}
      <View style={styles.headerActions}>
        <TouchableOpacity style={styles.headerButton} onPress={clearHistory}>
          <Ionicons name="refresh" size={20} color="#888" />
        </TouchableOpacity>
      </View>

      {/* Messages */}
      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(item) => item.id}
        renderItem={renderMessage}
        contentContainerStyle={styles.messagesList}
        showsVerticalScrollIndicator={false}
      />

      {/* Loading indicator */}
      {isLoading && (
        <View style={styles.loadingContainer}>
          <View style={styles.loadingBubble}>
            <ActivityIndicator size="small" color="#f59e0b" />
          </View>
        </View>
      )}

      {/* Input */}
      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          placeholder="Message Donna..."
          placeholderTextColor="#666"
          value={input}
          onChangeText={setInput}
          onSubmitEditing={handleSend}
          returnKeyType="send"
          multiline
          maxLength={500}
        />
        <TouchableOpacity
          style={[styles.sendButton, !input.trim() && styles.sendButtonDisabled]}
          onPress={handleSend}
          disabled={!input.trim() || isLoading}
        >
          <Ionicons name="send" size={20} color="#fff" />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0f',
  },
  headerActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a24',
  },
  headerButton: {
    padding: 8,
  },
  messagesList: {
    padding: 16,
    paddingBottom: 8,
  },
  messageRow: {
    marginBottom: 12,
    flexDirection: 'row',
  },
  messageRowUser: {
    justifyContent: 'flex-end',
  },
  messageBubble: {
    maxWidth: '85%',
    padding: 12,
    borderRadius: 16,
  },
  userBubble: {
    backgroundColor: 'rgba(245, 158, 11, 0.2)',
    borderBottomRightRadius: 4,
  },
  assistantBubble: {
    backgroundColor: '#1a1a24',
    borderBottomLeftRadius: 4,
  },
  messageText: {
    fontSize: 15,
    color: '#e5e5e5',
    lineHeight: 22,
  },
  userText: {
    color: '#fcd34d',
  },
  intentBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
    gap: 4,
  },
  intentText: {
    fontSize: 11,
    color: '#f59e0b',
    textTransform: 'capitalize',
  },
  confirmButtons: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#2a2a3a',
  },
  confirmButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    padding: 10,
    backgroundColor: 'rgba(34, 197, 94, 0.15)',
    borderRadius: 10,
  },
  confirmText: {
    color: '#22c55e',
    fontWeight: '500',
    fontSize: 13,
  },
  cancelButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    padding: 10,
    backgroundColor: '#2a2a3a',
    borderRadius: 10,
  },
  cancelText: {
    color: '#888',
    fontWeight: '500',
    fontSize: 13,
  },
  loadingContainer: {
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  loadingBubble: {
    backgroundColor: '#1a1a24',
    padding: 16,
    borderRadius: 16,
    borderBottomLeftRadius: 4,
    alignSelf: 'flex-start',
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 12,
    paddingBottom: Platform.OS === 'ios' ? 24 : 12,
    borderTopWidth: 1,
    borderTopColor: '#1a1a24',
    gap: 8,
  },
  input: {
    flex: 1,
    backgroundColor: '#1a1a24',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    color: '#fff',
    maxHeight: 100,
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#f59e0b',
    justifyContent: 'center',
    alignItems: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: '#2a2a3a',
  },
});


