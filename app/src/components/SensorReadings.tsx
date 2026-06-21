import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Reading } from '../types';
import { COLORS } from '../theme';

interface Props {
  readings: Reading;
}

interface SensorCell {
  icon: string;
  label: string;
  value: string;
}

export const SensorReadings: React.FC<Props> = ({ readings }) => {
  const cells: SensorCell[] = [
    {
      icon: '💧',
      label: 'Soil',
      value: `${readings.soil_pct.toFixed(1)}%`,
    },
    {
      icon: '☀️',
      label: 'Light',
      value: `${Math.round(readings.light_lux)} lux`,
    },
    {
      icon: '🌡️',
      label: 'Temp',
      value: `${readings.temp_c.toFixed(1)}°C`,
    },
    {
      icon: '💨',
      label: 'Humidity',
      value: `${readings.humidity_pct.toFixed(1)}%`,
    },
  ];

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>SENSORS</Text>
      <View style={styles.grid}>
        {cells.map((cell) => (
          <View key={cell.label} style={styles.cell}>
            <Text style={styles.cellIcon}>{cell.icon}</Text>
            <Text style={styles.cellLabel}>{cell.label}</Text>
            <Text style={styles.cellValue}>{cell.value}</Text>
          </View>
        ))}
      </View>
      {readings.conductivity_ppm !== undefined && (
        <View style={styles.conductivityRow}>
          <Text style={styles.cellIcon}>⚡</Text>
          <Text style={styles.cellLabel}>Conductivity</Text>
          <Text style={styles.cellValue}>
            {readings.conductivity_ppm.toFixed(0)} ppm
          </Text>
        </View>
      )}
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
  heading: {
    color: COLORS.accent,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 2,
    marginBottom: 12,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  cell: {
    width: '48%',
    backgroundColor: COLORS.bg,
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
    alignItems: 'center',
  },
  cellIcon: {
    fontSize: 22,
    marginBottom: 4,
  },
  cellLabel: {
    color: COLORS.textMuted,
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 1,
    textTransform: 'uppercase',
    marginBottom: 2,
  },
  cellValue: {
    color: COLORS.text,
    fontSize: 18,
    fontWeight: '700',
  },
  conductivityRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.bg,
    borderRadius: 10,
    padding: 12,
    marginTop: 2,
    gap: 8,
  },
});
