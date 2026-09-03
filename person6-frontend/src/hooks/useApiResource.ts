import { useCallback, useEffect, useRef, useState } from 'react';
import type { FetchState } from '../types';

interface Result<T> {
  data: T | undefined;
  state: FetchState;
  error: string | undefined;
  reload: () => void;
  /** Timestamp (ms) of the last successful fetch, so callers can show the
   * operator how stale a snapshot is instead of leaving it unstated. */
  lastUpdatedAt: number | undefined;
}

/**
 * Fetches a resource on mount (and whenever `deps` changes), tracking
 * loading/error/success state so every view can render a real empty,
 * loading, or error state instead of a blank screen.
 */
export function useApiResource<T>(
  fetcher: () => Promise<T>,
  deps: React.DependencyList = [],
  options?: { pollMs?: number; enabled?: boolean },
): Result<T> {
  const [data, setData] = useState<T>();
  const [state, setState] = useState<FetchState>('idle');
  const [error, setError] = useState<string>();
  const [lastUpdatedAt, setLastUpdatedAt] = useState<number>();
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const enabled = options?.enabled ?? true;

  const load = useCallback(() => {
    if (!enabled) {
      return () => {};
    }
    let cancelled = false;
    setState('loading');
    setError(undefined);
    fetcherRef
      .current()
      .then((res) => {
        if (cancelled) return;
        setData(res);
        setState('success');
        setLastUpdatedAt(Date.now());
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Something went wrong');
        setState('error');
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  useEffect(() => {
    if (!enabled) {
      setData(undefined);
      setState('idle');
      setError(undefined);
      return;
    }
    const cancel = load();
    if (!options?.pollMs) return cancel;
    const id = setInterval(load, options.pollMs);
    return () => {
      cancel();
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, ...deps]);

  return { data, state, error, reload: load, lastUpdatedAt };
}
