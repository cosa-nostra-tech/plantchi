import { PlantState, HistoryPoint, Species } from '../types';
import { loadConfig } from '../store/config';

async function getBaseUrl(): Promise<string> {
  const config = await loadConfig();
  return config.backendUrl.replace(/\/$/, '');
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const baseUrl = await getBaseUrl();
  const url = `${baseUrl}${path}`;

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `API error ${response.status} at ${path}: ${text}`
    );
  }

  return response.json() as Promise<T>;
}

/** Fetch the current state of a plant */
export async function getPlantState(plantId: string): Promise<PlantState> {
  return apiFetch<PlantState>(`/plants/${plantId}/state`);
}

/** Fetch historical sensor readings for a plant */
export async function getHistory(
  plantId: string,
  hours: number = 24
): Promise<HistoryPoint[]> {
  return apiFetch<HistoryPoint[]>(
    `/plants/${plantId}/history?hours=${hours}`
  );
}

/** Create a new plant, returns the new plant_id */
export async function createPlant(
  name: string,
  speciesKey: string
): Promise<{ plant_id: string }> {
  return apiFetch<{ plant_id: string }>('/plants', {
    method: 'POST',
    body: JSON.stringify({ name, species_key: speciesKey }),
  });
}

/** Search species by query string */
export async function searchSpecies(query: string): Promise<Species[]> {
  const encoded = encodeURIComponent(query);
  return apiFetch<Species[]>(`/species/search?q=${encoded}`);
}

/** List all plants */
export async function listPlants(): Promise<
  { plant_id: string; name: string; species_key: string }[]
> {
  return apiFetch<{ plant_id: string; name: string; species_key: string }[]>(
    '/plants'
  );
}
