import { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
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

export default function DigestScreen() {
  const { dailyDigest, fetchDailyDigest, user, messages } = useAppStore();
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDigest();
  }, []);

  // Refresh digest when messages change (in case a reminder was just created)
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    if (lastMessage?.intent === 'create_reminder' || 
        lastMessage?.content?.toLowerCase().includes('reminder')) {
      const timer = setTimeout(() => {
        loadDigest();
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [messages]);

  const loadDigest = async () => {
    setLoading(true);
    await fetchDailyDigest();
    setLoading(false);
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchDailyDigest();
    setRefreshing(false);
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  const getTimeOfDay = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'morning';
    if (hour < 17) return 'afternoon';
    return 'evening';
  };

  if (!user?.googleConnected) {
    return (
      <View style={styles.emptyContainer}>
        <View style={styles.emptyIcon}>
          <Text style={styles.emptyEmoji}>📋</Text>
        </View>
        <Text style={styles.emptyTitle}>Connect Your Calendar</Text>
        <Text style={styles.emptyText}>
          Connect your Google account in Settings to see your daily digest.
        </Text>
      </View>
    );
  }

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading your day...</Text>
      </View>
    );
  }

  const hasUnread = (dailyDigest?.unreadEmails || 0) > 0 || (dailyDigest?.unreadTeams || 0) > 0;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={colors.primary}
          colors={[colors.primary]}
        />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.greeting}>Good {getTimeOfDay()}!</Text>
        <Text style={styles.dateText}>{today}</Text>
      </View>

      {/* Summary Card */}
      <View style={styles.summaryCard}>
        <Text style={styles.summaryText}>
          {dailyDigest?.summary || "You're all set for today!"}
        </Text>
      </View>

      {/* Communications Summary */}
      {hasUnread && dailyDigest?.communicationsSummary && (
        <View style={styles.communicationsCard}>
          <View style={styles.communicationsHeader}>
            <Ionicons name="mail" size={18} color={colors.primary} />
            <Text style={styles.communicationsTitle}>Your Inbox Briefing</Text>
          </View>
          {(() => {
            // Parse HTML and render with proper formatting
            const text = dailyDigest.communicationsSummary;
            const lines = text.split('\n');
            const parts: JSX.Element[] = [];
            
            lines.forEach((line, lineIdx) => {
              if (!line.trim()) return;
              
              // Check for platform header
              if (line.includes('<strong>') && line.includes(':</strong>')) {
                const platform = line.replace(/<strong>|<\/strong>/g, '').replace(':', '').trim();
                parts.push(
                  <Text key={`header-${lineIdx}`} style={[styles.communicationsText, { fontWeight: '700', marginTop: lineIdx > 0 ? 12 : 0, marginBottom: 4, fontSize: 16 }]}>
                    {platform}:
                  </Text>
                );
              } else {
                // Regular line - parse <b> tags for bold
                const cleanLine = line.replace(/<strong>.*?<\/strong>/g, '').trim();
                if (!cleanLine) return;
                
                const boldRegex = /<b>(.*?)<\/b>/g;
                const lineParts: (string | JSX.Element)[] = [];
                let lastIndex = 0;
                let match;
                let keyCounter = 0;
                
                while ((match = boldRegex.exec(cleanLine)) !== null) {
                  // Add text before bold
                  if (match.index > lastIndex) {
                    lineParts.push(cleanLine.substring(lastIndex, match.index));
                  }
                  // Add bold text
                  lineParts.push(
                    <Text key={`bold-${lineIdx}-${keyCounter++}`} style={{ fontWeight: '700', color: colors.text }}>
                      {match[1]}
                    </Text>
                  );
                  lastIndex = match.index + match[0].length;
                }
                // Add remaining text
                if (lastIndex < cleanLine.length) {
                  lineParts.push(cleanLine.substring(lastIndex));
                }
                
                parts.push(
                  <Text key={`line-${lineIdx}`} style={[styles.communicationsText, { marginTop: 4 }]}>
                    {lineParts.length > 1 ? lineParts : cleanLine}
                  </Text>
                );
              }
            });
            
            return <View>{parts}</View>;
          })()}
          <View style={styles.communicationsStats}>
            {(dailyDigest.unreadEmailsGmail || 0) > 0 && (
              <Text style={styles.statText}>📧 {dailyDigest.unreadEmailsGmail} Gmail</Text>
            )}
            {(dailyDigest.unreadEmailsOutlook || 0) > 0 && (
              <Text style={styles.statText}>📧 {dailyDigest.unreadEmailsOutlook} Outlook</Text>
            )}
            {(dailyDigest.unreadTeams || 0) > 0 && (
              <Text style={styles.statText}>💬 {dailyDigest.unreadTeams} Teams</Text>
            )}
          </View>
        </View>
      )}

      {/* Meetings Section */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Ionicons name="calendar" size={18} color={colors.primary} />
          <Text style={styles.sectionTitle}>Today's Meetings</Text>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{dailyDigest?.meetingsCount || 0}</Text>
          </View>
        </View>

        {dailyDigest?.meetings && dailyDigest.meetings.length > 0 ? (
          dailyDigest.meetings.map((meeting) => (
            <View key={meeting.id} style={styles.meetingCard}>
              <View style={styles.meetingTime}>
                <Text style={styles.timeText}>{formatTime(meeting.start)}</Text>
              </View>
              <View style={styles.meetingInfo}>
                <Text style={styles.meetingTitle}>{meeting.summary}</Text>
                {meeting.attendees && meeting.attendees.length > 0 && (
                  <View style={styles.attendeesRow}>
                    <Ionicons name="people-outline" size={14} color={colors.textMuted} />
                    <Text style={styles.attendeesText}>
                      {meeting.attendees.length} attendee{meeting.attendees.length !== 1 ? 's' : ''}
                    </Text>
                  </View>
                )}
              </View>
            </View>
          ))
        ) : (
          <View style={styles.emptySection}>
            <Text style={styles.emptySectionText}>No meetings today</Text>
          </View>
        )}
      </View>

      {/* Reminders Section */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Ionicons name="notifications" size={18} color={colors.primary} />
          <Text style={styles.sectionTitle}>Reminders</Text>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{dailyDigest?.remindersCount || 0}</Text>
          </View>
        </View>

        {dailyDigest?.reminders && dailyDigest.reminders.length > 0 ? (
          dailyDigest.reminders.map((reminder) => (
            <View key={reminder.id} style={styles.reminderCard}>
              <View style={styles.reminderDot} />
              <View style={styles.reminderInfo}>
                <Text style={styles.reminderText}>{reminder.text}</Text>
                <Text style={styles.reminderTime}>
                  {formatTime(reminder.dueTime)}
                </Text>
              </View>
            </View>
          ))
        ) : (
          <View style={styles.emptySection}>
            <Text style={styles.emptySectionText}>No reminders for today</Text>
          </View>
        )}
      </View>

      <View style={styles.bottomPadding} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    padding: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
    gap: 12,
  },
  loadingText: {
    color: colors.textMuted,
    fontSize: 14,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
    backgroundColor: colors.background,
  },
  emptyIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.primaryLight,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  emptyEmoji: {
    fontSize: 36,
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
  header: {
    marginBottom: 20,
  },
  greeting: {
    fontSize: 28,
    fontWeight: '700',
    color: colors.text,
    fontFamily: Platform.OS === 'ios' ? 'Georgia' : 'serif',
  },
  dateText: {
    fontSize: 16,
    color: colors.textMuted,
    marginTop: 4,
  },
  summaryCard: {
    backgroundColor: colors.primaryLight,
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
  },
  summaryText: {
    fontSize: 16,
    color: colors.text,
    lineHeight: 24,
  },
  communicationsCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: colors.border,
  },
  communicationsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  communicationsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
  },
  communicationsText: {
    fontSize: 15,
    color: colors.text,
    lineHeight: 22,
    marginBottom: 12,
  },
  communicationsStats: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  statText: {
    fontSize: 13,
    color: colors.textMuted,
  },
  section: {
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  sectionTitle: {
    flex: 1,
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
  },
  badge: {
    backgroundColor: colors.surfaceAlt,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  badgeText: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textMuted,
  },
  meetingCard: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  meetingTime: {
    marginRight: 14,
    paddingTop: 2,
  },
  timeText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.primary,
  },
  meetingInfo: {
    flex: 1,
  },
  meetingTitle: {
    fontSize: 15,
    fontWeight: '500',
    color: colors.text,
    marginBottom: 4,
  },
  attendeesRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  attendeesText: {
    fontSize: 13,
    color: colors.textMuted,
  },
  reminderCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  reminderDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.primary,
    marginRight: 14,
  },
  reminderInfo: {
    flex: 1,
  },
  reminderText: {
    fontSize: 15,
    color: colors.text,
    marginBottom: 2,
  },
  reminderTime: {
    fontSize: 13,
    color: colors.textMuted,
  },
  emptySection: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 14,
    padding: 20,
    alignItems: 'center',
  },
  emptySectionText: {
    fontSize: 14,
    color: colors.textMuted,
  },
  bottomPadding: {
    height: 20,
  },
});
