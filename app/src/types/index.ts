export type PlantStateName =
  | 'HAPPY'
  | 'THRIVING'
  | 'THIRSTY'
  | 'DROWNING'
  | 'HUNGRY'
  | 'COLD'
  | 'HOT'
  | 'DIM'
  | 'SCORCHED'
  | 'SLEEPING';

export type Severity = 'ok' | 'warn' | 'critical';

export interface Reading {
  soil_pct: number;
  light_lux: number;
  temp_c: number;
  humidity_pct: number;
  conductivity_ppm?: number;
}

export interface PlantState {
  plant_id: string;
  name: string;
  state: PlantStateName;
  severity: Severity;
  readings: Reading;
  thresholds: Record<string, number>;
  last_updated: string;
}

export interface HistoryPoint {
  timestamp: string;
  soil_pct: number;
  light_lux: number;
  temp_c: number;
  humidity_pct: number;
}

export interface AppConfig {
  backendUrl: string;
  plantId: string;
  plantName: string;
}

export interface Species {
  key: string;
  name: string;
  common_name?: string;
  description?: string;
}
