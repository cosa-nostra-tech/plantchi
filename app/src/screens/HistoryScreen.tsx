import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  Dimensions,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { getHistory } from '../api/client';
import { loadConfig } from '../store/config';
import { HistoryPoint } from '../types';
import { COLORS, SPACING } from '../theme';
import { RootStackParamList } from '../../App';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'History'>;
};

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CHART_HEIGHT = 100;
const CHART_WIDTH = SCREEN_WIDTH - SPACING.md * 2 - 32; // card padding

function SparklineChart({
  data,
  color,
  minVal,
  maxVal,
}: {
  data: number[];
  color: string;
  minVal: number;
  maxVal: number;
}) {
  if (data.length === 0) return null;

  const range = maxVal - minVal || 1;
  const barWidth = Math.max(2, CHART_WIDTH / data.length - 1);

  return (
    <View style={[styles.chart, { height: CHART_HEIGHT, width: CHART_WIDTH }]}>
      {data.map((val, i) => {
        const heightPct = ((val - minVal) / range) * 0.9 + 0.05;
        const barHeight = Math.max(3, heightPct * CHART_HEIGHT);
        return (
          <View
            key={i}
            style={{
              position: 'absolute',
              bottom: 0,
              left: i * (barWidth + 1),
              width: barWidth,
              height: barHeight,
              backgroundColor: color,
              borderRadius: 1,
              opacity: 0.85,
            }}
          />
        );
      })}
    </View>
  );
}

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return ts;
  }
}

export const HistoryScreen: React.FC<Props> = ({ navigation }) => {
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const cfg = await loadConfig();
      if (!cfg.plantId) throw new Error('No plant configured.');
      const data = await getHistory(cfg.plantId, 24);
      setHistory(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load history');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const soilData = history.map((h) => h.soil_pct);
  const tempData  = history.map((h) => h.temp_c);
  const lightData = history.map((h) => h.light_lux);

  const minSoil = Math.min(...soilData, 0);
  const maxSoil = Math.max(...soilData, 100);
  const minTemp = Math.min(...tempData, 15);
  const maxTemp = Math.max(...tempData, 35);
  const minLight = Math.min(...lightData, 0);
  const maxLight = Math.max(...lightData, 1000);

  // Show every Nth point for the reading list
  const stride = Math.max(1, Math.floor(history.length / 12));
  const listPoints = history.filter((_, i) => i % stride === 0);

  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={loading}
          onRefresh={fetchHistory}
          tintColor={COLORS.accent}
          colors={[COLORS.accent]}
        />
      }
    >
      <View style={styles.headerRow}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backBtn}
        >
          <Text style={styles.backBtnText}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.screenTitle}>24h History</Text>
        <View style={{ width: 60 }} />
      </View>

      {error && (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>⚠️ {error}</Text>
        </View>
      )}

      {loading && history.length === 0 ? (
        <View style={styles.centered}>
          <ActivityIndicator color={COLORS.accent} size="large" />
          <Text style={styles.loadingText}>Loading history…</Text>
        </View>
      ) : history.length === 0 ? (
        <View style={styles.centered}>
          <Text style={styles.emptyEmoji}>📊</Text>
          <Text style={styles.emptyText}>No history data available yet.</Text>
          <Text style={styles.emptyHint}>
            Data will appear after your plant has been monitored for a while.
          </Text>
        </View>
      ) : (
        <>
          {/* Soil moisture sparkline */}
          <View style={styles.chartCard}>
            <Text style={styles.chartTitle}>💧 SOIL MOISTURE</Text>
            <View style={styles.chartMinMax}>
              <Text style={styles.chartStat}>Min: {Math.min(...soilData).toFixed(1)}%</Text>
              <Text style={styles.chartStat}>Max: {Math.max(...soilData).toFixed(1)}%</Text>
              <Text style={styles.chartStat}>Now: {soilData[soilData.length - 1]?.toFixed(1)}%</Text>
            </View>
            <SparklineChart
              data={soilData}
              color={COLORS.ok}
              minVal={minSoil}
              maxVal={maxSoil}
            />
          </View>

          {/* Temperature sparkline */}
          <View style={styles.chartCard}>
            <Text style={styles.chartTitle}>🌡️ TEMPERATURE</Text>
            <View style={styles.chartMinMax}>
              <Text style={styles.chartStat}>Min: {Math.min(...tempData).toFixed(1)}°C</Text>
              <Text style={styles.chartStat}>Max: {Math.max(...tempData).toFixed(1)}°C</Text>
              <Text style={styles.chartStat}>Now: {tempData[tempData.length - 1]?.toFixed(1)}°C</Text>
            </View>
            <SparklineChart
              data={tempData}
              color={COLORS.warn}
              minVal={minTemp}
              maxVal={maxTemp}
            />
          </View>

          {/* Light sparkline */}
          <View style={styles.chartCard}>
            <Text style={styles.chartTitle}>☀️ LIGHT</Text>
            <View style={styles.chartMinMax}>
              <Text style={styles.chartStat}>Min: {Math.round(Math.min(...lightData))} lux</Text>
              <Text style={styles.chartStat}>Max: {Math.round(Math.max(...lightData))} lux</Text>
              <Text style={styles.chartStat}>Now: {Math.round(lightData[lightData.length - 1] ?? 0)} lux</Text>
            </View>
            <SparklineChart
              data={lightData}
              color={COLORS.accent}
              minVal={minLight}
              maxVal={maxLight}
            />
          </View>

          {/* Reading list (sampled) */}
          <Text style={styles.sectionHeading}>READINGS LOG</Text>
          {listPoints.map((pt, i) => (
            <View key={i} style={styles.readingRow}>
              <Text style={styles.readingTime}>{formatTimestamp(pt.timestamp)}</Text>
              <View style={styles.readingVals}>
                <Text style={styles.readingVal}>💧{pt.soil_pct.toFixed(1)}%</Text>
                <Text style={styles.readingVal}>🌡️{pt.temp_c.toFixed(1)}°</Text>
                <Text style={styles.readingVal}>☀️{Math.round(pt.light_lux)}</Text>
                <Text style={styles.readingVal}>💨{pt.humidity_pct.toFixed(0)}%</Text>
              </View>
            </View>
          ))}
        </>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: COLORS.bg,
  },
  content: {
    padding: SPACING.md,
    paddingTop: SPACING.lg,
    paddingBottom: 60,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: SPACING.lg,
  },
  backBtn: {
    width: 60,
  },
  backBtnText: {
    color: COLORS.accent,
    fontSize: 15,
    fontWeight: '700',
  },
  screenTitle: {
    color: COLORS.text,
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 1,
  },
  errorBanner: {
    backgroundColor: '#2a0000',
    borderRadius: 10,
    padding: SPACING.sm,
    marginBottom: SPACING.sm,
    borderWidth: 1,
    borderColor: COLORS.critical,
  },
  errorText: {
    color: COLORS.critical,
    fontSize: 13,
  },
  centered: {
    paddingVertical: 60,
    alignItems: 'center',
  },
  loadingText: {
    color: COLORS.textMuted,
    marginTop: SPACING.md,
    fontSize: 14,
  },
  emptyEmoji: {
    fontSize: 48,
    marginBottom: 12,
  },
  emptyText: {
    color: COLORS.text,
    fontSize: 16,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: 8,
  },
  emptyHint: {
    color: COLORS.textMuted,
    fontSize: 13,
    textAlign: 'center',
    paddingHorizontal: 20,
  },
  chartCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    marginBottom: SPACING.md,
    overflow: 'hidden',
  },
  chartTitle: {
    color: COLORS.accent,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 2,
    marginBottom: 8,
  },
  chartMinMax: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 10,
  },
  chartStat: {
    color: COLORS.textMuted,
    fontSize: 11,
    fontWeight: '600',
  },
  chart: {
    position: 'relative',
    backgroundColor: COLORS.bg,
    borderRadius: 6,
    overflow: 'hidden',
  },
  sectionHeading: {
    color: COLORS.accent,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 2,
    marginBottom: SPACING.sm,
    marginTop: SPACING.sm,
  },
  readingRow: {
    backgroundColor: COLORS.card,
    borderRadius: 10,
    padding: 12,
    marginBottom: 6,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  readingTime: {
    color: COLORS.textMuted,
    fontSize: 12,
    fontWeight: '600',
    width: 50,
  },
  readingVals: {
    flexDirection: 'row',
    gap: 10,
    flex: 1,
    justifyContent: 'flex-end',
  },
  readingVal: {
    color: COLORS.text,
    fontSize: 12,
    fontWeight: '600',
  },
});
