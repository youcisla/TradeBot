"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { AgentEvent } from "./swr";

const WS_URL =
  typeof window !== "undefined"
    ? (window as unknown as { NEXT_PUBLIC_WS_URL?: string }).NEXT_PUBLIC_WS_URL ?? null
    : null;

const MAX_EVENTS = 200;

/**
 * Global WebSocket hook.
 * Call once at the AppShell level; all pages share the same connection via context.
 */
export function useWebSocket(onMessage?: (events: AgentEvent[]) => void) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!WS_URL) return;

    try {
      const ws = new WebSocket(WS_URL);

      ws.onmessage = (msg) => {
        if (!mountedRef.current) return;
        try {
          const incoming: AgentEvent[] = JSON.parse(msg.data);
          setEvents((prev) => {
            const merged = [...incoming, ...prev];
            return merged.slice(0, MAX_EVENTS);
          });
          onMessage?.(incoming);
        } catch {
          // malformed message — ignore
        }
      };

      ws.onerror = () => {
        //沉默
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        // Reconnect after 3s
        setTimeout(connect, 3_000);
      };

      wsRef.current = ws;
    } catch {
      // WebSocket not available
    }
  }, [onMessage]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      wsRef.current?.close();
    };
  }, [connect]);

  return events;
}

/**
 * Fire-and-forget POST to the commands API.
 */
export async function sendCommand(action: string, params?: Record<string, unknown>) {
  await fetch("/api/commands", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, ...params }),
  });
}
