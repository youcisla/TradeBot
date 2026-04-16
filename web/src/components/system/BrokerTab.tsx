"use client";

import { useEffect, useState } from "react";
import { useAppShell } from "@/components/AppShell";

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

  return (
    <div className="flex flex-col gap-3">
      {/* Connection status */}
      <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
        <StatusCard label="Broker"   value={status?.broker_name ?? "—"} />
        <StatusCard label="Account"  value={status?.broker_account ?? "—"} />
        <StatusCard label="Server"   value={status?.broker_server ?? "—"} />
        <StatusCard label="Leverage" value={status?.leverage ?? "—"} />
      </div>

      {/* Account list */}
      <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-3 py-3 flex flex-col gap-2">
        <span
          className="font-mono text-[9px] font-bold uppercase"
          style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.06em" }}
        >
          Accounts
        </span>
        {accounts.length === 0 ? (
          <p className="font-mono text-sm m-0" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
            No account data
          </p>
        ) : (
          accounts.map((acc) => (
            <div key={acc.id} className="flex items-center gap-3 py-1.5 border-b border-[var(--border)] last:border-b-0">
              <span className="font-mono text-sm font-bold flex-1" style={{ fontFamily: "var(--font-mono)", color: "var(--text-1)" }}>
                {acc.account_number}
              </span>
              <span className="font-mono text-[10px]" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
                {acc.server}
              </span>
              <span className="font-mono text-[10px]" style={{ fontFamily: "var(--font-mono)", color: "var(--text-2)" }}>
                {acc.name}
              </span>
              {acc.is_demo && (
                <span
                  className="font-mono text-[9px] font-bold rounded px-1 py-0.5"
                  style={{ fontFamily: "var(--font-mono)", color: "var(--orange)", border: "1px solid var(--orange)", letterSpacing: "0.04em" }}
                >
                  DEMO
                </span>
              )}
              <span
                className="rounded-full flex-shrink-0"
                style={{
                  width: 8,
                  height: 8,
                  background: acc.is_active ? "var(--green)" : "var(--red)",
                  boxShadow: acc.is_active ? "0 0 6px var(--green)" : "0 0 6px var(--red)",
                }}
              />
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function StatusCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-3 py-3 flex flex-col gap-1">
      <span
        className="font-mono text-[9px] font-bold uppercase"
        style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.06em" }}
      >
        {label}
      </span>
      <span
        className="font-mono text-sm font-bold"
        style={{ fontFamily: "var(--font-mono)", color: "var(--text-1)" }}
      >
        {value}
      </span>
    </div>
  );
}
