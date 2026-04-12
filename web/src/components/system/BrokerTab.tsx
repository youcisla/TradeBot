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
    <div style={styles.root}>
      {/* Connection status */}
      <div style={styles.statusRow}>
        <div style={styles.statusCard}>
          <span style={styles.statusLabel}>Broker</span>
          <span style={styles.statusValue}>{status?.broker_name ?? "—"}</span>
        </div>
        <div style={styles.statusCard}>
          <span style={styles.statusLabel}>Account</span>
          <span style={styles.statusValue}>{status?.broker_account ?? "—"}</span>
        </div>
        <div style={styles.statusCard}>
          <span style={styles.statusLabel}>Server</span>
          <span style={styles.statusValue}>{status?.broker_server ?? "—"}</span>
        </div>
        <div style={styles.statusCard}>
          <span style={styles.statusLabel}>Leverage</span>
          <span style={styles.statusValue}>{status?.leverage ?? "—"}</span>
        </div>
      </div>

      {/* Account list */}
      <div style={styles.tableCard}>
        <span style={styles.tableTitle}>Accounts</span>
        {accounts.length === 0 ? (
          <p style={styles.empty}>No account data</p>
        ) : (
          accounts.map((acc) => (
            <div key={acc.id} style={styles.row}>
              <span style={styles.accNum}>{acc.account_number}</span>
              <span style={styles.accServer}>{acc.server}</span>
              <span style={styles.accBroker}>{acc.name}</span>
              {acc.is_demo && <span style={styles.demoBadge}>DEMO</span>}
              <span
                style={{
                  ...styles.connDot,
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

const styles: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-3)",
  },
  statusRow: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: "var(--space-3)",
  },
  statusCard: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    padding: "var(--space-3)",
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  statusLabel: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 700,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  statusValue: {
    fontFamily: "var(--font-mono)",
    fontSize: 12,
    fontWeight: 700,
    color: "var(--text-1)",
  },
  tableCard: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    padding: "var(--space-3)",
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
  },
  tableTitle: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 700,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  empty: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    color: "var(--text-3)",
    margin: 0,
  },
  row: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-3)",
    padding: "6px 0",
    borderBottom: "1px solid var(--border)",
  },
  accNum: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    fontWeight: 700,
    color: "var(--text-1)",
    flex: 1,
  },
  accServer: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    color: "var(--text-3)",
  },
  accBroker: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    color: "var(--text-2)",
  },
  demoBadge: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 700,
    color: "var(--orange)",
    border: "1px solid var(--orange)",
    borderRadius: 3,
    padding: "1px 4px",
    letterSpacing: "0.04em",
  },
  connDot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    flexShrink: 0,
  },
};
