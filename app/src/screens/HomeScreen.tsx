import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useFocusEffect } from '@react-navigation/native';
import { PlantCharacter } from '../components/PlantCharacter';
import { SensorReadings } from '../components/SensorReadings';
import { StateBar } from '../components/StateBar';
import { usePlantState } from '../hooks/usePlantState';
import { loadConfig } from '../store/config';
import { COLORS, SPACING } from '../theme';
import { RootStackParamList } from '../../App';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Home'>;
};

export const HomeScreen: React.FC<Props> = ({ navigation }) => {
  const [plantId, setPlantId] = useState<string | null>(null);
  const [plantLabel, setPlantLabel] = useState<string>('');
  const [configLoaded, setConfigLoaded] = useState(false);

  const { plantState, loading, error, refresh, lastRefreshed } =
    usePlantState(plantId);

  // Load config on every focus (in case user just came back from Setup)
  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      loadConfig().then((cfg) => {
        if (cancelled) return;
        if (!cfg.plantId) {
          navigation.replace('Setup');
          return;
        }
        setPlantId(cfg.plantId);
        setPlantLabel(cfg.plantName || 'My Plant');
        setConfigLoaded(true);
      });
      return () => { cancelled = true; };
    }, [navigation])
  );

  const formattedTime = lastRefreshed
    ? lastRefreshed.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    : null;

  if (!configLoaded) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color={COLORS.accent} size="large" />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={loading}
          onRefresh={refresh}
          tintColor={COLORS.accent}
          colors={[COLORS.accent]}
        />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.plantName}>{plantLabel}</Text>
        <TouchableOpacity
          onPress={() => navigation.navigate('History')}
          style={styles.historyBtn}
        >
          <Text style={styles.historyBtnText}>History</Text>
        </TouchableOpacity>
      </View>

      {/* Error banner */}
      {error && (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>⚠️ {error}</Text>
        </View>
      )}

      {/* Loading skeleton or plant display */}
      {loading && !plantState ? (
        <View style={styles.centered}>
          <ActivityIndicator color={COLORS.accent} size="large" />
          <Text style={styles.loadingText}>Checking on your plant…</Text>
        </View>
      ) : plantState ? (
        <>
          <PlantCharacter
            state={plantState.state}
            severity={plantState.severity}
          />
          <StateBar severity={plantState.severity} />
          <SensorReadings readings={plantState.readings} />

          {/* Last updated */}
          <View style={styles.footer}>
            <Text style={styles.footerText}>
              {formattedTime
                ? `Last updated ${formattedTime}`
                : 'Fetching latest data…'}
            </Text>
            <TouchableOpacity onPress={refresh} style={styles.refreshBtn}>
              <Text style={styles.refreshBtnText}>↺ Refresh</Text>
            </TouchableOpacity>
          </View>
        </>
      ) : (
        <View style={styles.centered}>
          <Text style={styles.loadingText}>No data yet. Pull to refresh.</Text>
        </View>
      )}

      {/* Settings shortcut */}
      <TouchableOpacity
        onPress={() => navigation.navigate('Setup')}
        style={styles.settingsBtn}
      >
        <Text style={styles.settingsBtnText}>⚙ Settings</Text>
      </TouchableOpacity>
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
    paddingBottom: 40,
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.sm,
  },
  plantName: {
    color: COLORS.text,
    fontSize: 28,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  historyBtn: {
    backgroundColor: COLORS.card,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderWidth: 1,
    borderColor: COLORS.accent,
  },
  historyBtnText: {
    color: COLORS.accent,
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.5,
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
    fontWeight: '600',
  },
  loadingText: {
    color: COLORS.textMuted,
    marginTop: SPACING.md,
    fontSize: 14,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: SPACING.sm,
    paddingHorizontal: 4,
  },
  footerText: {
    color: COLORS.textMuted,
    fontSize: 11,
    letterSpacing: 0.3,
  },
  refreshBtn: {
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  refreshBtnText: {
    color: COLORS.accent,
    fontSize: 13,
    fontWeight: '700',
  },
  settingsBtn: {
    marginTop: SPACING.xl,
    alignSelf: 'center',
    paddingHorizontal: 18,
    paddingVertical: 8,
  },
  settingsBtnText: {
    color: COLORS.textMuted,
    fontSize: 13,
    letterSpacing: 1,
  },
});
