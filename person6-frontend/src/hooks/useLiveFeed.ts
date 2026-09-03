import { useEffect, useRef, useState } from 'react';
import { WS_URL } from '../api/client';
import type { LiveDetection } from '../types';

export type WsStatus = 'connecting' | 'open' | 'closed' | 'reconnecting';

const MAX_ENTRIES = 20;
const BASE_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 15000;

export function useLiveFeed() {
  const [entries, setEntries] = useState<LiveDetection[]>([]);
  const [status, setStatus] = useState<WsStatus>('connecting');
  const attemptRef = useRef(0);
  const socketRef = useRef<WebSocket | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const unmountedRef = useRef(false);

  useEffect(() => {
    unmountedRef.current = false;

    const connect = () => {
      if (unmountedRef.current) return;
      setStatus(attemptRef.current === 0 ? 'connecting' : 'reconnecting');

      let socket: WebSocket;
      try {
        socket = new WebSocket(WS_URL);
      } catch {
        scheduleReconnect();
        return;
      }
      socketRef.current = socket;

      socket.onopen = () => {
        attemptRef.current = 0;
        setStatus('open');
      };

      socket.onmessage = (evt) => {
        try {
          const parsed = JSON.parse(evt.data) as LiveDetection;
          const withMeta: LiveDetection = {
            ...parsed,
            _receivedAt: Date.now(),
            _key: `${parsed.observation_id ?? ''}-${Date.now()}-${Math.random()}`,
          };
          setEntries((prev) => [withMeta, ...prev].slice(0, MAX_ENTRIES));
        } catch {
          // Ignore malformed frames rather than crashing the feed.
        }
      };

      socket.onclose = () => {
        if (unmountedRef.current) return;
        setStatus('closed');
        scheduleReconnect();
      };

      socket.onerror = () => {
        socket.close();
      };
    };

    const scheduleReconnect = () => {
      attemptRef.current += 1;
      const delay = Math.min(BASE_BACKOFF_MS * 2 ** (attemptRef.current - 1), MAX_BACKOFF_MS);
      timeoutRef.current = setTimeout(connect, delay);
    };

    connect();

    return () => {
      unmountedRef.current = true;
      clearTimeout(timeoutRef.current);
      socketRef.current?.close();
    };
  }, []);

  return { entries, status };
}
