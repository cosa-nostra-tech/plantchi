import AsyncStorage from '@react-native-async-storage/async-storage';
import { AppConfig } from '../types';

const KEYS = {
  BACKEND_URL: 'plantchi_backend_url',
  PLANT_ID: 'plantchi_plant_id',
  PLANT_NAME: 'plantchi_plant_name',
};

const DEFAULT_CONFIG: AppConfig = {
  backendUrl: 'http://localhost:8000',
  plantId: '',
  plantName: '',
};

export async function loadConfig(): Promise<AppConfig> {
  try {
    const [backendUrl, plantId, plantName] = await AsyncStorage.multiGet([
      KEYS.BACKEND_URL,
      KEYS.PLANT_ID,
      KEYS.PLANT_NAME,
    ]);

    return {
      backendUrl: backendUrl[1] ?? DEFAULT_CONFIG.backendUrl,
      plantId: plantId[1] ?? DEFAULT_CONFIG.plantId,
      plantName: plantName[1] ?? DEFAULT_CONFIG.plantName,
    };
  } catch (e) {
    console.error('Failed to load config:', e);
    return DEFAULT_CONFIG;
  }
}

export async function saveConfig(config: Partial<AppConfig>): Promise<void> {
  try {
    const pairs: [string, string][] = [];
    if (config.backendUrl !== undefined)
      pairs.push([KEYS.BACKEND_URL, config.backendUrl]);
    if (config.plantId !== undefined)
      pairs.push([KEYS.PLANT_ID, config.plantId]);
    if (config.plantName !== undefined)
      pairs.push([KEYS.PLANT_NAME, config.plantName]);
    await AsyncStorage.multiSet(pairs);
  } catch (e) {
    console.error('Failed to save config:', e);
    throw e;
  }
}

export async function clearConfig(): Promise<void> {
  try {
    await AsyncStorage.multiRemove([
      KEYS.BACKEND_URL,
      KEYS.PLANT_ID,
      KEYS.PLANT_NAME,
    ]);
  } catch (e) {
    console.error('Failed to clear config:', e);
    throw e;
  }
}
