import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Severity } from '../types';
import { COLORS } from '../theme';

interface Props {
  severity: Severity;
}

const SEVERITY_CONFIG: Record<
  Severity,
  { color: string; label: string; fill: number }
> = {
  ok:       { color: COLORS.ok,       label: 'ALL GOOD',  fill: 1.0 },
  warn:     { color: COLORS.warn,     label: 'ATTENTION', fill: 0.55 },
  critical: { color: COLORS.critical, label: 'CRITICAL',  fill: 0.15 },
};

export const StateBar: React.FC<Props> = ({ severity }) => {
  const cfg = SEVERITY_CONFIG[severity];

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headingText}>STATUS</Text>
        <Text style={[styles.labelText, { color: cfg.color }]}>
          {cfg.label}
        </Text>
      </View>
      <View style={styles.track}>
        <View
          style={[
            styles.fill,
            {
              width: `${cfg.fill * 100}%` as `${number}%`,
              backgroundColor: cfg.color,
            },
          ]}
        />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    marginVertical: 8,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  headingText: {
    color: COLORS.textMuted,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 2,
  },
  labelText: {
    fontSize: 13,
    fontWeight: '800',
    letterSpacing: 1.5,
  },
  track: {
    height: 12,
    backgroundColor: COLORS.bg,
    borderRadius: 6,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: 6,
  },
});
