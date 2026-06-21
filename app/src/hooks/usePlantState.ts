import { useState, useEffect, useCallback, useRef } from 'react';
import { PlantState } from '../types';
import { getPlantState } from '../api/client';

const POLL_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

interface UsePlantStateResult {
  plantState: PlantState | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  lastRefreshed: Date | null;
}

export function usePlantState(plantId: string | null): UsePlantStateResult {
  const [plantState, setPlantState] = useState<PlantState | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    if (!plantId) {
      setPlantState(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const state = await getPlantState(plantId);
      setPlantState(state);
      setLastRefreshed(new Date());
    } catch (e: unknown) {
      const message =
        e instanceof Error ? e.message : 'Failed to fetch plant state';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [plantId]);

  useEffect(() => {
    if (!plantId) {
      setPlantState(null);
      return;
    }

    // Initial fetch
    refresh();

    // Set up polling
    intervalRef.current = setInterval(() => {
      refresh();
    }, POLL_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [plantId, refresh]);

  return { plantState, loading, error, refresh, lastRefreshed };
}
