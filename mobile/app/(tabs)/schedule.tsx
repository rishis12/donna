import { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  ActivityIndicator,
  RefreshControl,
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
};

export default function ScheduleScreen() {
  const { events, fetchEvents, user } = useAppStore();
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents = async () => {
    setLoading(true);
    await fetchEvents();
    setLoading(false);
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchEvents();
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

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    });
  };

  const isToday = (dateStr: string) => {
    return new Date(dateStr).toDateString() === new Date().toDateString();
  };

  const isTomorrow = (dateStr: string) => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return new Date(dateStr).toDateString() === tomorrow.toDateString();
  };

  const getRelativeDay = (dateStr: string) => {
    if (isToday(dateStr)) return 'Today';
    if (isTomorrow(dateStr)) return 'Tomorrow';
    return formatDate(dateStr);
  };

  const getDuration = (start: string, end: string) => {
    const startDate = new Date(start);
    const endDate = new Date(end);
    const mins = (endDate.getTime() - startDate.getTime()) / (1000 * 60);
    if (mins >= 60) return `${Math.round(mins / 60)}h`;
    return `${mins}m`;
  };

  const groupedEvents = events.reduce((acc, event) => {
    const day = new Date(event.start).toDateString();
    if (!acc[day]) acc[day] = [];
    acc[day].push(event);
    return acc;
  }, {} as Record<string, typeof events>);

  const sortedDays = Object.keys(groupedEvents).sort(
    (a, b) => new Date(a).getTime() - new Date(b).getTime()
  );

  if (!user?.googleConnected) {
    return (
      <View style={styles.emptyContainer}>
        <View style={styles.emptyIcon}>
          <Text style={styles.emptyEmoji}>📅</Text>
        </View>
        <Text style={styles.emptyTitle}>Connect Your Calendar</Text>
        <Text style={styles.emptyText}>
          Connect your Google Calendar in Settings to see your schedule here.
        </Text>
      </View>
    );
  }

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading schedule...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={sortedDays}
        keyExtractor={(item) => item}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.primary}
            colors={[colors.primary]}
          />
        }
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <View style={styles.emptyIcon}>
              <Text style={styles.emptyEmoji}>☕</Text>
            </View>
            <Text style={styles.emptyTitle}>All Clear!</Text>
            <Text style={styles.emptyText}>
              No upcoming events. Ask Donna to schedule something!
            </Text>
          </View>
        }
        renderItem={({ item: day }) => (
          <View style={styles.daySection}>
            <View
              style={[
                styles.dayHeader,
                isToday(groupedEvents[day][0].start) && styles.dayHeaderToday,
              ]}
            >
              <Text
                style={[
                  styles.dayText,
                  isToday(groupedEvents[day][0].start) && styles.dayTextToday,
                ]}
              >
                {getRelativeDay(groupedEvents[day][0].start)}
              </Text>
              {isToday(groupedEvents[day][0].start) && (
                <View style={styles.todayBadge}>
                  <Text style={styles.todayBadgeText}>Today</Text>
                </View>
              )}
            </View>

            {groupedEvents[day].map((event) => (
              <View key={event.id} style={styles.eventCard}>
                <View style={styles.eventTime}>
                  <Text style={styles.startTime}>{formatTime(event.start)}</Text>
                  <View style={styles.timeDivider} />
                  <Text style={styles.endTime}>{formatTime(event.end)}</Text>
                </View>

                <View style={styles.eventContent}>
                  <Text style={styles.eventTitle} numberOfLines={2}>
                    {event.summary || 'Untitled Event'}
                  </Text>
                  <View style={styles.eventMeta}>
                    <Ionicons name="time-outline" size={14} color={colors.textMuted} />
                    <Text style={styles.eventDuration}>
                      {getDuration(event.start, event.end)}
                    </Text>
                    {event.attendees && event.attendees.length > 0 && (
                      <>
                        <View style={styles.metaDot} />
                        <Ionicons name="people-outline" size={14} color={colors.textMuted} />
                        <Text style={styles.eventAttendees}>
                          {event.attendees.length}
                        </Text>
                      </>
                    )}
                  </View>
                </View>
              </View>
            ))}
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  listContent: {
    padding: 16,
    paddingBottom: 40,
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
    marginTop: 60,
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
  daySection: {
    marginBottom: 20,
  },
  dayHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    marginBottom: 8,
  },
  dayHeaderToday: {},
  dayText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    fontFamily: Platform.OS === 'ios' ? 'Georgia' : 'serif',
  },
  dayTextToday: {
    color: colors.primary,
  },
  todayBadge: {
    backgroundColor: colors.primaryLight,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    marginLeft: 10,
  },
  todayBadgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.primary,
  },
  eventCard: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  eventTime: {
    alignItems: 'center',
    marginRight: 16,
    minWidth: 60,
  },
  startTime: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.primary,
  },
  timeDivider: {
    width: 1,
    height: 16,
    backgroundColor: colors.border,
    marginVertical: 4,
  },
  endTime: {
    fontSize: 12,
    color: colors.textMuted,
  },
  eventContent: {
    flex: 1,
    justifyContent: 'center',
  },
  eventTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: colors.text,
    marginBottom: 6,
  },
  eventMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  eventDuration: {
    fontSize: 13,
    color: colors.textMuted,
    marginLeft: 2,
  },
  metaDot: {
    width: 3,
    height: 3,
    borderRadius: 1.5,
    backgroundColor: colors.textMuted,
    marginHorizontal: 6,
  },
  eventAttendees: {
    fontSize: 13,
    color: colors.textMuted,
    marginLeft: 2,
  },
});
