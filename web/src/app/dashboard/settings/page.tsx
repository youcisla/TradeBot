"use client";

import { useEffect, useState, useCallback } from "react";
import PageHeader from "@/components/PageHeader";
import TerminalInput from "@/components/TerminalInput";

interface BrokerAccount {
  id: number;
  name: string;
  account_number: string;
  server: string;
  is_demo: boolean;
  is_active: boolean;
  created_at: string;
  last_connected: string | null;
}

interface FormData {
  name: string;
  account_number: string;
  password: string;
  server: string;
  is_demo: boolean;
}

const EMPTY_FORM: FormData = {
  name: "",
  account_number: "",
  password: "",
  server: "",
  is_demo: true,
};

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 6 }}>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9, fontWeight: 700, letterSpacing: "0.14em",
          textTransform: "uppercase", color: "#607888",
        }}>
          {label}
        </span>
        {hint && (
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 8.5, color: "#607888",
          }}>
            {hint}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

/* TerminalInput now imported from @/components/TerminalInput */

export default function SettingsPage() {
  const [accounts, setAccounts]   = useState<BrokerAccount[]>([]);
  const [loading, setLoading]     = useState(true);
  const [showForm, setShowForm]   = useState(false);
  const [editId, setEditId]       = useState<number | null>(null);
  const [form, setForm]           = useState<FormData>(EMPTY_FORM);
  const [saving, setSaving]       = useState(false);
  const [error, setError]         = useState("");
  const [deleting, setDeleting]   = useState<number | null>(null);

  const load = useCallback(() => {
    fetch("/api/broker/accounts")
      .then((r) => r.json())
      .then((data) => { if (Array.isArray(data)) setAccounts(data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditId(null);
    setShowForm(false);
    setError("");
  };

  const handleSave = async () => {
    if (!form.name || !form.account_number || !form.server) {
      setError("Name, account number, and server are required.");
      return;
    }
    if (!editId && !form.password) {
      setError("Password is required for new accounts.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const url    = editId ? `/api/broker/accounts/${editId}` : "/api/broker/accounts";
      const method = editId ? "PUT" : "POST";
      const body: Record<string, unknown> = {
        name:           form.name,
        account_number: form.account_number,
        server:         form.server,
        is_demo:        form.is_demo,
      };
      if (form.password) body.password = form.password;
      const r = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const err = await r.json();
        throw new Error(err.error || "Failed to save");
      }
      resetForm();
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleActivate = async (id: number) => {
    await fetch(`/api/broker/accounts/${id}`, { method: "PATCH" });
    load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this broker account?")) return;
    setDeleting(id);
    await fetch(`/api/broker/accounts/${id}`, { method: "DELETE" });
    setDeleting(null);
    load();
  };

  const handleEdit = (a: BrokerAccount) => {
    setEditId(a.id);
    setForm({
      name:           a.name,
      account_number: a.account_number,
      password:       "",
      server:         a.server,
      is_demo:        a.is_demo,
    });
    setShowForm(true);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>

      {/* Header */}
      <PageHeader subsystem="Configuration" title="Settings" accent="#00ff88" />
        <p style={{
          marginTop: -12, fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11, color: "#607888", lineHeight: 1.6,
        }}>
          The <span style={{ color: "#00ff88" }}>active</span> account is used when the bot next starts.
          Restart the bot after switching accounts.
        </p>

      {/* Account list */}
      {loading ? (
        <div style={{
          fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
          color: "#607888", padding: "20px 0",
        }}>
          Connecting to broker database…
        </div>
      ) : accounts.length === 0 ? (
        <div style={{
          background: "#0a0a12", border: "1px solid #1c1c28",
          borderRadius: 8, padding: "32px 24px", textAlign: "center",
        }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
            color: "#3a5248", marginBottom: 8,
          }}>
            No broker accounts configured.
          </div>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace", fontSize: 9.5,
            color: "#607888",
          }}>
            Bot is using credentials from .env as fallback
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {accounts.map((a) => (
            <div
              key={a.id}
              style={{
                background: "#0a0a12",
                border: `1px solid ${a.is_active ? "#00ff8840" : "#1c1c28"}`,
                borderLeft: `3px solid ${a.is_active ? "#00ff88" : "#1c1c28"}`,
                borderRadius: 8,
                padding: "14px 18px",
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                gap: 16,
              }}
            >
              {/* Info */}
              <div style={{ flex: 1, minWidth: 220 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 13, fontWeight: 700, color: "#c0ccd8",
                  }}>
                    {a.name}
                  </span>
                  {a.is_active && (
                    <span style={{
                      display: "inline-block",
                      padding: "1px 7px", borderRadius: 3,
                      fontSize: 8.5, fontWeight: 700, letterSpacing: "0.1em",
                      fontFamily: "'JetBrains Mono', monospace",
                      background: "rgba(0,255,136,0.12)",
                      color: "#00ff88",
                      border: "1px solid rgba(0,255,136,0.25)",
                    }}>
                      ACTIVE
                    </span>
                  )}
                  <span style={{
                    display: "inline-block",
                    padding: "1px 7px", borderRadius: 3,
                    fontSize: 8.5, fontWeight: 700, letterSpacing: "0.08em",
                    fontFamily: "'JetBrains Mono', monospace",
                    background: a.is_demo ? "rgba(245,197,24,0.12)" : "rgba(255,68,85,0.12)",
                    color: a.is_demo ? "#f5c518" : "#ff4455",
                    border: `1px solid ${a.is_demo ? "rgba(245,197,24,0.25)" : "rgba(255,68,85,0.25)"}`,
                  }}>
                    {a.is_demo ? "DEMO" : "LIVE"}
                  </span>
                </div>
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 10, color: "#607888",
                }}>
                  Account: <span style={{ color: "#9aa8b8" }}>{a.account_number}</span>
                  {" · "}
                  Server: <span style={{ color: "#9aa8b8" }}>{a.server}</span>
                </div>
                {a.last_connected && (
                  <div style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 9, color: "#607888", marginTop: 3,
                  }}>
                    Last connected: {new Date(a.last_connected).toLocaleString()}
                  </div>
                )}
              </div>

              {/* Actions */}
              <div style={{ display: "flex", gap: 8 }}>
                {!a.is_active && (
                  <ActionBtn
                    onClick={() => handleActivate(a.id)}
                    color="#00ff88"
                  >
                    ACTIVATE
                  </ActionBtn>
                )}
                <ActionBtn
                  onClick={() => handleEdit(a)}
                  color="#4da6ff"
                >
                  EDIT
                </ActionBtn>
                <ActionBtn
                  onClick={() => handleDelete(a.id)}
                  color="#ff4455"
                  disabled={deleting === a.id}
                >
                  {deleting === a.id ? "…" : "DELETE"}
                </ActionBtn>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add / Edit form */}
      {!showForm ? (
        <div>
          <button
            onClick={() => { resetForm(); setShowForm(true); }}
            style={{
              padding: "9px 20px",
              background: "rgba(0,255,136,0.08)",
              border: "1px solid rgba(0,255,136,0.3)",
              borderRadius: 5,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11, fontWeight: 700, letterSpacing: "0.08em",
              color: "#00ff88",
              cursor: "pointer",
              transition: "background 0.15s, box-shadow 0.15s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(0,255,136,0.15)";
              (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 0 14px rgba(0,255,136,0.2)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(0,255,136,0.08)";
              (e.currentTarget as HTMLButtonElement).style.boxShadow = "none";
            }}
          >
            + ADD ACCOUNT
          </button>
        </div>
      ) : (
        <div style={{
          background: "#0a0a12",
          border: "1px solid #1c1c28",
          borderTop: "2px solid #00ff88",
          borderRadius: 8,
          padding: "20px 24px",
        }}>
          {/* Form header */}
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 9, fontWeight: 700, letterSpacing: "0.18em",
            textTransform: "uppercase", color: "#00ff88",
            marginBottom: 20,
          }}>
            {editId ? "Edit Broker Account" : "New Broker Account"}
          </div>

          {/* Error */}
          {error && (
            <div style={{
              background: "rgba(255,68,85,0.08)",
              border: "1px solid rgba(255,68,85,0.25)",
              borderRadius: 4, padding: "8px 12px",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10.5, color: "#ff4455",
              marginBottom: 16,
            }}>
              {error}
            </div>
          )}

          {/* Fields grid */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: 16,
            marginBottom: 16,
          }}>
            <Field label="Display Name">
              <TerminalInput
                value={form.name}
                onChange={(v) => setForm({ ...form, name: v })}
                placeholder="e.g. PUPrime Demo"
              />
            </Field>

            <Field label="Account Number">
              <TerminalInput
                value={form.account_number}
                onChange={(v) => setForm({ ...form, account_number: v })}
                placeholder="e.g. 700074018"
              />
            </Field>

            <Field
              label="Password"
              hint={editId ? "(leave blank to keep current)" : undefined}
            >
              <TerminalInput
                type="password"
                value={form.password}
                onChange={(v) => setForm({ ...form, password: v })}
                placeholder="••••••••"
              />
            </Field>

            <Field label="Server">
              <TerminalInput
                value={form.server}
                onChange={(v) => setForm({ ...form, server: v })}
                placeholder="e.g. PUPrime-Demo"
              />
            </Field>
          </div>

          {/* Demo toggle */}
          <div
            onClick={() => setForm({ ...form, is_demo: !form.is_demo })}
            style={{
              display: "inline-flex", alignItems: "center", gap: 10,
              cursor: "pointer", marginBottom: 20, userSelect: "none",
            }}
          >
            {/* Toggle track */}
            <div style={{
              width: 36, height: 20, borderRadius: 10,
              background: form.is_demo ? "rgba(245,197,24,0.2)" : "#0e0e10",
              border: `1px solid ${form.is_demo ? "rgba(245,197,24,0.4)" : "#1c1c28"}`,
              position: "relative",
              transition: "background 0.2s, border-color 0.2s",
            }}>
              <div style={{
                width: 14, height: 14,
                borderRadius: "50%",
                background: form.is_demo ? "#f5c518" : "#607888",
                position: "absolute",
                top: 2,
                left: form.is_demo ? 18 : 2,
                transition: "left 0.2s, background 0.2s",
                boxShadow: form.is_demo ? "0 0 6px rgba(245,197,24,0.6)" : "none",
              }} />
            </div>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10.5,
              color: form.is_demo ? "#f5c518" : "#607888",
              letterSpacing: "0.04em",
            }}>
              {form.is_demo ? "DEMO account" : "LIVE account"}
            </span>
          </div>

          {/* Buttons */}
          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{
                padding: "8px 20px",
                background: saving ? "rgba(0,255,136,0.05)" : "rgba(0,255,136,0.1)",
                border: "1px solid rgba(0,255,136,0.35)",
                borderRadius: 4,
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11, fontWeight: 700, letterSpacing: "0.08em",
                color: saving ? "rgba(0,255,136,0.3)" : "#00ff88",
                cursor: saving ? "not-allowed" : "pointer",
                opacity: saving ? 0.6 : 1,
                transition: "background 0.15s",
              }}
              onMouseEnter={(e) => {
                if (!saving) (e.currentTarget as HTMLButtonElement).style.background = "rgba(0,255,136,0.18)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background = saving ? "rgba(0,255,136,0.05)" : "rgba(0,255,136,0.1)";
              }}
            >
              {saving ? "SAVING…" : editId ? "UPDATE" : "ADD ACCOUNT"}
            </button>
            <button
              onClick={resetForm}
              style={{
                padding: "8px 20px",
                background: "transparent",
                border: "1px solid #1c1c28",
                borderRadius: 4,
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11, fontWeight: 700, letterSpacing: "0.08em",
                color: "#607888",
                cursor: "pointer",
                transition: "border-color 0.15s, color 0.15s",
              }}
              onMouseEnter={(e) => {
                const btn = e.currentTarget as HTMLButtonElement;
                btn.style.borderColor = "#607888";
                btn.style.color = "#4a5a6a";
              }}
              onMouseLeave={(e) => {
                const btn = e.currentTarget as HTMLButtonElement;
                btn.style.borderColor = "#1c1c28";
                btn.style.color = "#607888";
              }}
            >
              CANCEL
            </button>
          </div>
        </div>
      )}

      {/* Info section */}
      <div style={{
        background: "#0a0a12", border: "1px solid #1c1c28",
        borderLeft: "3px solid #4da6ff",
        borderRadius: 8, padding: "14px 18px",
      }}>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9, fontWeight: 700, letterSpacing: "0.14em",
          textTransform: "uppercase", color: "#4da6ff",
          marginBottom: 10,
        }}>
          Connection Notes
        </div>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10.5, color: "#607888", lineHeight: 1.7,
          display: "flex", flexDirection: "column", gap: 4,
        }}>
          {[
            ["Activation",   "Switch accounts via ACTIVATE — takes effect on next bot restart"],
            ["Password",     "Stored encrypted in the local database, never transmitted externally"],
            ["Demo → Live",  "Always validate strategy on demo before enabling a live account"],
            ["Fallback",     "If no account is active, the bot reads MT5_LOGIN / MT5_PASSWORD from .env"],
          ].map(([label, text]) => (
            <div key={label} style={{ display: "flex", gap: 10 }}>
              <span style={{ color: "#607888", minWidth: 80 }}>{label}</span>
              <span>{text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ActionBtn({
  onClick,
  color,
  children,
  disabled = false,
}: {
  onClick: () => void;
  color: string;
  children: React.ReactNode;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "5px 12px",
        background: `${color}10`,
        border: `1px solid ${color}40`,
        borderRadius: 4,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 9.5, fontWeight: 700, letterSpacing: "0.08em",
        color: disabled ? `${color}40` : color,
        cursor: disabled ? "not-allowed" : "pointer",
        transition: "background 0.15s, box-shadow 0.15s",
      }}
      onMouseEnter={(e) => {
        if (!disabled) {
          (e.currentTarget as HTMLButtonElement).style.background = `${color}20`;
          (e.currentTarget as HTMLButtonElement).style.boxShadow = `0 0 8px ${color}30`;
        }
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLButtonElement).style.background = `${color}10`;
        (e.currentTarget as HTMLButtonElement).style.boxShadow = "none";
      }}
    >
      {children}
    </button>
  );
}
