"use client";

import { useEffect, useState } from "react";
import { useAppShell } from "@/components/AppShell";
import { Panel } from "@/components/ui/panel";
import { StatusBadge } from "@/components/ui/status-badge";

interface BrokerAccount {
  id: number;
  account_number: string;
  server: string;
  name: string;
  is_demo: boolean;
  is_active: boolean;
  created_at: string;
  last_connected: string | null;
}

export default function BrokerTab() {
  const { status } = useAppShell();
  const [accounts, setAccounts] = useState<BrokerAccount[]>([]);

  useEffect(() => {
    fetch("/api/broker/accounts")
      .then((r) => r.json())
      .then((d) => setAccounts(Array.isArray(d) ? d : []))
      .catch(() => setAccounts([]));
  }, []);

  const stats = [
    { label: "Broker",    value: status?.broker_name    ?? "—" },
    { label: "Account",   value: status?.broker_account ?? "—" },
    { label: "Server",    value: status?.broker_server  ?? "—" },
    { label: "Leverage",  value: status?.leverage       ?? "—" },
  ];

  return (
    <div className="flex flex-col gap-3">
      {/* Connection status */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {stats.map(({ label, value }) => (
          <div
            key={label}
            className="rounded p-3 flex flex-col gap-1"
            style={{ background: "var(--bg-2)", border: "1px solid var(--border)" }}
          >
            <span
              className="font-mono text-xs font-bold uppercase tracking-widest"
              style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 9 }}
            >
              {label}
            </span>
            <span
              className="font-mono font-bold"
              style={{ color: "var(--text-1)", fontFamily: "var(--font-mono)", fontSize: 13 }}
            >
              {value}
            </span>
          </div>
        ))}
      </div>

      {/* Account list */}
      <Panel title="Accounts">
        {accounts.length === 0 ? (
          <p className="font-mono text-sm" style={{ color: "var(--text-3)", margin: 0 }}>
            No account data
          </p>
        ) : (
          <div className="flex flex-col">
            {accounts.map((acc) => (
              <div
                key={acc.id}
                className="flex items-center gap-3 py-2 border-b"
                style={{ borderColor: "var(--border)" }}
              >
                <span
                  className="font-mono font-bold flex-1"
                  style={{ color: "var(--text-1)", fontFamily: "var(--font-mono)", fontSize: 12 }}
                >
                  {acc.account_number}
                </span>
                <span
                  className="font-mono"
                  style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 10 }}
                >
                  {acc.server}
                </span>
                <span
                  className="font-mono"
                  style={{ color: "var(--text-2)", fontFamily: "var(--font-mono)", fontSize: 10 }}
                >
                  {acc.name}
                </span>
                {acc.is_demo && (
                  <StatusBadge label="DEMO" variant="warning" size="sm" />
                )}
                <span
                  className="rounded-full flex-shrink-0"
                  style={{
                    width: 8, height: 8,
                    background: acc.is_active ? "var(--green)" : "var(--red)",
                    boxShadow: acc.is_active ? "0 0 6px var(--green)" : "0 0 6px var(--red)",
                  }}
                />
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
