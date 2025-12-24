import { useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAppStore } from '../../stores/appStore';
import { useState } from 'react';

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

  // Group events by day
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
        <Ionicons name="calendar-outline" size={64} color="#333" />
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
        <ActivityIndicator size="large" color="#f59e0b" />
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
            tintColor="#f59e0b"
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="calendar-outline" size={64} color="#333" />
            <Text style={styles.emptyTitle}>No Upcoming Events</Text>
            <Text style={styles.emptyText}>
              Ask Donna to schedule something for you!
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
            </View>

            {groupedEvents[day].map((event) => (
              <View key={event.id} style={styles.eventCard}>
                <View style={styles.timeColumn}>
                  <Text style={styles.startTime}>{formatTime(event.start)}</Text>
                  <View style={styles.timeLine} />
                  <Text style={styles.endTime}>{formatTime(event.end)}</Text>
                </View>

                <View style={styles.eventContent}>
                  <Text style={styles.eventTitle} numberOfLines={2}>
                    {event.summary || 'Untitled Event'}
                  </Text>
                  {event.attendees && event.attendees.length > 0 && (
                    <View style={styles.attendeesRow}>
                      <Ionicons name="people" size={12} color="#888" />
                      <Text style={styles.attendeesText}>
                        {event.attendees.length} attendee
                        {event.attendees.length > 1 ? 's' : ''}
                      </Text>
                    </View>
                  )}
                </View>

                <View style={styles.durationBadge}>
                  <Ionicons name="time-outline" size={12} color="#666" />
                  <Text style={styles.durationText}>
                    {getDuration(event.start, event.end)}
                  </Text>
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
    backgroundColor: '#0a0a0f',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0a0a0f',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
    marginTop: 100,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#888',
    marginTop: 16,
  },
  emptyText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginTop: 8,
  },
  daySection: {
    marginBottom: 16,
  },
  dayHeader: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  dayHeaderToday: {
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
  },
  dayText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#888',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  dayTextToday: {
    color: '#f59e0b',
  },
  eventCard: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginTop: 8,
    padding: 12,
    backgroundColor: '#1a1a24',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#2a2a3a',
  },
  timeColumn: {
    alignItems: 'center',
    marginRight: 12,
    minWidth: 50,
  },
  startTime: {
    fontSize: 13,
    fontWeight: '600',
    color: '#f59e0b',
  },
  timeLine: {
    width: 1,
    height: 12,
    backgroundColor: '#2a2a3a',
    marginVertical: 4,
  },
  endTime: {
    fontSize: 11,
    color: '#666',
  },
  eventContent: {
    flex: 1,
    justifyContent: 'center',
  },
  eventTitle: {
    fontSize: 15,
    fontWeight: '500',
    color: '#e5e5e5',
  },
  attendeesRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 4,
  },
  attendeesText: {
    fontSize: 12,
    color: '#888',
  },
  durationBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    backgroundColor: '#0a0a0f',
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  durationText: {
    fontSize: 11,
    color: '#666',
  },
});


