import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { PlantStateName, Severity } from '../types';
import { COLORS } from '../theme';

interface StateDisplay {
  emoji: string;
  label: string;
}

const STATE_MAP: Record<PlantStateName, StateDisplay> = {
  HAPPY:    { emoji: '😊', label: 'Happy!' },
  THRIVING: { emoji: '🌟', label: 'Thriving!' },
  THIRSTY:  { emoji: '😢', label: 'Thirsty...' },
  DROWNING: { emoji: '💀', label: 'Drowning!' },
  HUNGRY:   { emoji: '🍽️', label: 'Hungry' },
  COLD:     { emoji: '🥶', label: 'Cold!' },
  HOT:      { emoji: '🥵', label: 'Too hot!' },
  DIM:      { emoji: '🌑', label: 'Too dark' },
  SCORCHED: { emoji: '☀️', label: 'Scorching!' },
  SLEEPING: { emoji: '😴', label: 'Sleeping' },
};

const SEVERITY_BORDER: Record<Severity, string> = {
  ok:       COLORS.ok,
  warn:     COLORS.warn,
  critical: COLORS.critical,
};

interface Props {
  state: PlantStateName;
  severity: Severity;
}

export const PlantCharacter: React.FC<Props> = ({ state, severity }) => {
  const display = STATE_MAP[state] ?? { emoji: '🌿', label: state };
  const borderColor = SEVERITY_BORDER[severity];

  return (
    <View style={[styles.container, { borderColor }]}>
      <Text style={styles.emoji}>{display.emoji}</Text>
      <Text style={[styles.label, { color: borderColor }]}>
        {display.label}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.card,
    borderRadius: 20,
    borderWidth: 3,
    paddingVertical: 28,
    paddingHorizontal: 40,
    marginVertical: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 8,
  },
  emoji: {
    fontSize: 96,
    lineHeight: 120,
    textAlign: 'center',
  },
  label: {
    marginTop: 10,
    fontSize: 22,
    fontWeight: '800',
    letterSpacing: 1.5,
    textAlign: 'center',
  },
});
