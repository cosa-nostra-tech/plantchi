import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Alert,
  FlatList,
  Keyboard,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { loadConfig, saveConfig } from '../store/config';
import { createPlant, searchSpecies } from '../api/client';
import { Species } from '../types';
import { COLORS, SPACING } from '../theme';
import { RootStackParamList } from '../../App';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Setup'>;
};

export const SetupScreen: React.FC<Props> = ({ navigation }) => {
  const [backendUrl, setBackendUrl] = useState('http://localhost:8000');
  const [plantName, setPlantName] = useState('');
  const [speciesQuery, setSpeciesQuery] = useState('');
  const [speciesResults, setSpeciesResults] = useState<Species[]>([]);
  const [selectedSpecies, setSelectedSpecies] = useState<Species | null>(null);
  const [speciesLoading, setSpeciesLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Pre-fill from stored config
  useEffect(() => {
    loadConfig().then((cfg) => {
      if (cfg.backendUrl) setBackendUrl(cfg.backendUrl);
      if (cfg.plantName) setPlantName(cfg.plantName);
    });
  }, []);

  // Debounced species search
  useEffect(() => {
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    if (!speciesQuery.trim() || speciesQuery.length < 2) {
      setSpeciesResults([]);
      return;
    }
    searchTimeout.current = setTimeout(async () => {
      setSpeciesLoading(true);
      try {
        // Temporarily save backend URL for the API call
        await saveConfig({ backendUrl: backendUrl.trim() });
        const results = await searchSpecies(speciesQuery);
        setSpeciesResults(results.slice(0, 10));
      } catch {
        setSpeciesResults([]);
      } finally {
        setSpeciesLoading(false);
      }
    }, 500);

    return () => {
      if (searchTimeout.current) clearTimeout(searchTimeout.current);
    };
  }, [speciesQuery, backendUrl]);

  const handleSave = async () => {
    if (!plantName.trim()) {
      Alert.alert('Missing Name', 'Please enter a name for your plant.');
      return;
    }
    if (!backendUrl.trim()) {
      Alert.alert('Missing URL', 'Please enter the backend URL.');
      return;
    }

    setSaving(true);
    Keyboard.dismiss();

    try {
      // Save URL first so createPlant uses the right endpoint
      await saveConfig({ backendUrl: backendUrl.trim() });

      const { plant_id } = await createPlant(
        plantName.trim(),
        selectedSpecies?.key ?? ''
      );

      await saveConfig({
        backendUrl: backendUrl.trim(),
        plantId: plant_id,
        plantName: plantName.trim(),
      });

      navigation.replace('Home');
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      Alert.alert('Setup Failed', msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
    >
      <View style={styles.titleRow}>
        <Text style={styles.logoEmoji}>🌱</Text>
        <Text style={styles.title}>PLANTCHI</Text>
      </View>
      <Text style={styles.subtitle}>Setup your plant companion</Text>

      {/* Backend URL */}
      <View style={styles.fieldGroup}>
        <Text style={styles.label}>BACKEND URL</Text>
        <TextInput
          style={styles.input}
          value={backendUrl}
          onChangeText={setBackendUrl}
          placeholder="http://localhost:8000"
          placeholderTextColor={COLORS.textMuted}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
          returnKeyType="done"
        />
        <Text style={styles.hint}>
          Enter the URL of your Plantchi FastAPI server
        </Text>
      </View>

      {/* Plant name */}
      <View style={styles.fieldGroup}>
        <Text style={styles.label}>PLANT NAME</Text>
        <TextInput
          style={styles.input}
          value={plantName}
          onChangeText={setPlantName}
          placeholder="e.g. Fernanda"
          placeholderTextColor={COLORS.textMuted}
          autoCapitalize="words"
          returnKeyType="done"
          maxLength={32}
        />
      </View>

      {/* Species search */}
      <View style={styles.fieldGroup}>
        <Text style={styles.label}>SPECIES (OPTIONAL)</Text>
        <TextInput
          style={styles.input}
          value={speciesQuery}
          onChangeText={setSpeciesQuery}
          placeholder="Search species…"
          placeholderTextColor={COLORS.textMuted}
          autoCapitalize="none"
          autoCorrect={false}
          returnKeyType="search"
        />
        {speciesLoading && (
          <ActivityIndicator
            color={COLORS.accent}
            size="small"
            style={styles.speciesLoader}
          />
        )}
        {selectedSpecies && (
          <View style={styles.selectedBadge}>
            <Text style={styles.selectedBadgeText}>
              ✓ {selectedSpecies.name}
            </Text>
            <TouchableOpacity onPress={() => setSelectedSpecies(null)}>
              <Text style={styles.clearBadge}>✕</Text>
            </TouchableOpacity>
          </View>
        )}
        {speciesResults.length > 0 && !selectedSpecies && (
          <View style={styles.speciesList}>
            {speciesResults.map((sp) => (
              <TouchableOpacity
                key={sp.key}
                style={styles.speciesItem}
                onPress={() => {
                  setSelectedSpecies(sp);
                  setSpeciesQuery('');
                  setSpeciesResults([]);
                }}
              >
                <Text style={styles.speciesName}>{sp.name}</Text>
                {sp.common_name && (
                  <Text style={styles.speciesCommon}>{sp.common_name}</Text>
                )}
              </TouchableOpacity>
            ))}
          </View>
        )}
        <Text style={styles.hint}>
          Optional — sets care thresholds automatically
        </Text>
      </View>

      {/* Save button */}
      <TouchableOpacity
        style={[styles.saveBtn, saving && styles.saveBtnDisabled]}
        onPress={handleSave}
        disabled={saving}
      >
        {saving ? (
          <ActivityIndicator color={COLORS.bg} size="small" />
        ) : (
          <Text style={styles.saveBtnText}>CONNECT PLANT →</Text>
        )}
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
    paddingTop: 48,
    paddingBottom: 60,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    marginBottom: 6,
  },
  logoEmoji: {
    fontSize: 40,
  },
  title: {
    color: COLORS.accent,
    fontSize: 36,
    fontWeight: '900',
    letterSpacing: 6,
  },
  subtitle: {
    color: COLORS.textMuted,
    fontSize: 14,
    textAlign: 'center',
    letterSpacing: 1,
    marginBottom: SPACING.xl,
  },
  fieldGroup: {
    marginBottom: SPACING.lg,
  },
  label: {
    color: COLORS.accent,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 2,
    marginBottom: 8,
  },
  input: {
    backgroundColor: COLORS.inputBg,
    color: COLORS.text,
    borderRadius: 10,
    padding: 14,
    fontSize: 15,
    borderWidth: 1,
    borderColor: COLORS.border,
    fontWeight: '500',
  },
  hint: {
    color: COLORS.textMuted,
    fontSize: 11,
    marginTop: 6,
    letterSpacing: 0.3,
  },
  speciesLoader: {
    marginTop: 8,
    alignSelf: 'flex-start',
  },
  selectedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#002a15',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginTop: 8,
    borderWidth: 1,
    borderColor: COLORS.ok,
    gap: 8,
  },
  selectedBadgeText: {
    color: COLORS.ok,
    fontSize: 13,
    fontWeight: '700',
    flex: 1,
  },
  clearBadge: {
    color: COLORS.textMuted,
    fontSize: 14,
  },
  speciesList: {
    backgroundColor: COLORS.card,
    borderRadius: 10,
    marginTop: 6,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  speciesItem: {
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  speciesName: {
    color: COLORS.text,
    fontSize: 14,
    fontWeight: '600',
  },
  speciesCommon: {
    color: COLORS.textMuted,
    fontSize: 12,
    marginTop: 2,
  },
  saveBtn: {
    backgroundColor: COLORS.accent,
    borderRadius: 14,
    padding: 18,
    alignItems: 'center',
    marginTop: SPACING.md,
  },
  saveBtnDisabled: {
    opacity: 0.5,
  },
  saveBtnText: {
    color: COLORS.bg,
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 2,
  },
});
