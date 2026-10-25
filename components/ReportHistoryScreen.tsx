
import React, { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { subscribeToReportChanges } from '../utils/reportSync';
import { FieldReport, REPORTS_STORAGE_KEY } from '../utils/reportStorage';

type Report = FieldReport;

type Props = {
  onBack: () => void;
};

export default function ReportHistoryScreen({ onBack }: Props) {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

  const loadReports = useCallback(async () => {
    try {
      const raw = await AsyncStorage.getItem(REPORTS_STORAGE_KEY);
      const saved: Report[] = raw ? JSON.parse(raw) : [];
      setReports(saved);
    } catch (error) {
      console.log('Failed to load reports:', error);
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initialLoad = setTimeout(() => { void loadReports(); }, 0);
    const unsubscribe = subscribeToReportChanges(() => { void loadReports(); });
    return () => {
      clearTimeout(initialLoad);
      unsubscribe();
    };
  }, [loadReports]);

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
    >
      <TouchableOpacity onPress={onBack} style={styles.back}>
        <Text style={styles.backText}>← Back to dashboard</Text>
      </TouchableOpacity>

      <Text style={styles.eyebrow}>TURTLEWAY FIELD TOOLS</Text>
      <Text style={styles.title}>Report history</Text>
      <Text style={styles.subtitle}>
        Your saved observations, including reports recorded offline.
      </Text>

      <TouchableOpacity onPress={loadReports} style={styles.refresh}>
        <Text style={styles.refreshText}>↻ Refresh reports</Text>
      </TouchableOpacity>

      {loading ? (
        <Text style={styles.empty}>Loading reports...</Text>
      ) : reports.length === 0 ? (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyIcon}>📋</Text>
          <Text style={styles.emptyTitle}>No reports yet</Text>
          <Text style={styles.empty}>
            Your saved field observations will appear here.
          </Text>
        </View>
      ) : (
        reports.map((report) => (
          <View key={report.id} style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.type}>{report.type}</Text>

              <View
                style={[
                  styles.badge,
                  report.syncStatus === 'synced'
                    ? styles.synced
                    : styles.pending,
                ]}
              >
                <Text style={styles.badgeText}>
                  {report.syncStatus === 'synced'
                    ? 'SYNCED'
                    : 'ON DEVICE'}
                </Text>
              </View>
            </View>

            <Text style={styles.sector}>📍 {report.sector}</Text>

            {report.locationSource ? (
              <Text style={styles.locationSource}>
                {report.locationSource === 'gps'
                  ? 'GPS location'
                  : report.locationSource === 'preset'
                    ? 'Coastal sector'
                    : 'Manual location'}
              </Text>
            ) : null}

            {typeof report.latitude === 'number' && typeof report.longitude === 'number' ? (
              <Text style={styles.coordinates}>
                {report.latitude.toFixed(6)}, {report.longitude.toFixed(6)}
              </Text>
            ) : null}

            {report.notes ? (
              <Text style={styles.notes}>{report.notes}</Text>
            ) : null}

            <Text style={styles.date}>
              {new Date(report.createdAt).toLocaleString()}
            </Text>

            <Text style={styles.status}>
              {report.syncStatus === 'synced'
                ? 'Received by server'
                : 'Waiting to sync — authority has not received this report'}
            </Text>
            <Text style={styles.reviewStatus}>
              {report.reviewStatus && report.reviewStatus !== 'not_reviewed'
                ? `Authority status: ${report.reviewStatus.replaceAll('_', ' ')}`
                : 'Not reviewed by an authorized conservation authority'}
            </Text>
          </View>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#F7F6F0' },
  content: { padding: 20, paddingBottom: 40 },
  back: { paddingVertical: 12, marginBottom: 12 },
  backText: { color: '#174D3A', fontSize: 16, fontWeight: '700' },
  eyebrow: {
    color: '#387653',
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 1.5,
  },
  title: {
    color: '#163D2B',
    fontSize: 29,
    fontWeight: '800',
    marginTop: 8,
  },
  subtitle: {
    color: '#58665D',
    fontSize: 15,
    lineHeight: 22,
    marginTop: 8,
    marginBottom: 18,
  },
  refresh: {
    alignSelf: 'flex-start',
    backgroundColor: '#E0F0E5',
    borderRadius: 10,
    padding: 11,
    marginBottom: 16,
  },
  refreshText: { color: '#176B45', fontWeight: '700' },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 15,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E2E8DF',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 8,
  },
  type: {
    color: '#20372A',
    fontSize: 17,
    fontWeight: '800',
    flex: 1,
  },
  badge: {
    borderRadius: 7,
    paddingHorizontal: 8,
    paddingVertical: 5,
  },
  pending: { backgroundColor: '#FFF1D8' },
  synced: { backgroundColor: '#DDF3E4' },
  badgeText: { fontSize: 10, fontWeight: '800', color: '#28563A' },
  sector: { color: '#42634D', marginTop: 10, fontSize: 13 },
  locationSource: { color: '#66766D', marginTop: 4, fontSize: 11, fontWeight: '700' },
  coordinates: { color: '#66766D', marginTop: 3, fontSize: 11, fontVariant: ['tabular-nums'] },
  notes: { color: '#34443A', marginTop: 10, lineHeight: 21 },
  date: { color: '#78847B', fontSize: 11, marginTop: 12 },
  status: {
    color: '#875B12',
    fontSize: 12,
    lineHeight: 18,
    marginTop: 9,
  },
  reviewStatus: {
    color: '#66766D',
    fontSize: 12,
    lineHeight: 18,
    marginTop: 5,
  },
  emptyCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 15,
    padding: 24,
    alignItems: 'center',
    marginTop: 10,
  },
  emptyIcon: { fontSize: 35 },
  emptyTitle: {
    color: '#20372A',
    fontSize: 18,
    fontWeight: '800',
    marginTop: 10,
  },
  empty: { color: '#66766D', marginTop: 12, lineHeight: 21 },
});
