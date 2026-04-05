"use client";

import { useEffect, useState, useCallback } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

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

interface BotStatus {
  broker?: string;
  account_number?: string;
  server?: string;
  db?: string;
  version?: string;
  bot_version?: string;
}

interface FormData {
  name: string;
  account_number: string;
  password: string;
  server: string;
  is_demo: boolean;
}

const EMPTY_FORM: FormData = {
  name: "", account_number: "", password: "", server: "", is_demo: true,
};

// ── Design tokens ─────────────────────────────────────────────────────────────

const SF: React.CSSProperties = {
  fontFamily: `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`,
};

// ── iOS Grouped Section ───────────────────────────────────────────────────────

function Section({ title, footer, children }: { title?: string; footer?: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 32 }}>
      {title && (
        <div style={{
          ...SF,
          fontSize: 13,
          fontWeight: 400,
          color: "rgba(235,235,245,0.6)",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
          marginBottom: 8,
          paddingLeft: 4,
        }}>
          {title}
        </div>
      )}
      <div style={{
        background: "#1C1C1E",
        borderRadius: 12,
        overflow: "hidden",
      }}>
        {children}
      </div>
      {footer && (
        <div style={{
          ...SF,
          fontSize: 13,
          color: "rgba(235,235,245,0.3)",
          paddingTop: 8,
          paddingLeft: 4,
        }}>
          {footer}
        </div>
      )}
    </div>
  );
}

function Row({
  label,
  value,
  valueColor,
  chevron,
  last,
  danger,
  children,
  onClick,
}: {
  label: string;
  value?: string;
  valueColor?: string;
  chevron?: boolean;
  last?: boolean;
  danger?: boolean;
  children?: React.ReactNode;
  onClick?: () => void;
}) {
  return (
    <>
      <div
        onClick={onClick}
        style={{
          display: "flex",
          alignItems: "center",
          minHeight: 44,
          padding: "10px 16px",
          cursor: onClick ? "pointer" : "default",
          gap: 12,
          transition: "background 0.1s",
        }}
        onMouseEnter={(e) => {
          if (onClick) (e.currentTarget as HTMLDivElement).style.background = "rgba(120,120,128,0.18)";
        }}
        onMouseLeave={(e) => {
          if (onClick) (e.currentTarget as HTMLDivElement).style.background = "transparent";
        }}
      >
        <span style={{
          ...SF,
          fontSize: 17,
          color: danger ? "#FF453A" : "#FFFFFF",
          flex: 1,
        }}>
          {label}
        </span>
        {children && <div style={{ display: "flex", alignItems: "center" }}>{children}</div>}
        {value && !children && (
          <span style={{
            ...SF,
            fontSize: 17,
            color: valueColor || "rgba(235,235,245,0.6)",
            flexShrink: 0,
          }}>
            {value}
          </span>
        )}
        {chevron && (
          <svg width="8" height="13" viewBox="0 0 8 13" fill="none" style={{ opacity: 0.3, marginLeft: 4, flexShrink: 0 }}>
            <path d="M1 1l6 5.5L1 12" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </div>
      {!last && (
        <div style={{
          height: "0.5px",
          background: "rgba(84,84,88,0.65)",
          marginLeft: 16,
        }} />
      )}
    </>
  );
}

// ── iOS Toggle ────────────────────────────────────────────────────────────────

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div
      onClick={() => onChange(!value)}
      style={{
        width: 51,
        height: 31,
        borderRadius: 16,
        background: value ? "#30D158" : "rgba(120,120,128,0.36)",
        cursor: "pointer",
        position: "relative",
        transition: "background 0.2s",
        flexShrink: 0,
      }}
    >
      <div style={{
        position: "absolute",
        top: 2,
        left: value ? 22 : 2,
        width: 27,
        height: 27,
        borderRadius: "50%",
        background: "#FFFFFF",
        boxShadow: "0 2px 6px rgba(0,0,0,0.3)",
        transition: "left 0.2s",
      }} />
    </div>
  );
}

// ── iOS Input ─────────────────────────────────────────────────────────────────

function IOSInput({
  value,
  onChange,
  placeholder,
  type = "text",
  autoFocus,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  autoFocus?: boolean;
}) {
  const [focused, setFocused] = useState(false);
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      placeholder={placeholder}
      autoFocus={autoFocus}
      style={{
        ...SF,
        width: "100%",
        height: 44,
        background: "rgba(120,120,128,0.24)",
        border: `1px solid ${focused ? "#0A84FF" : "transparent"}`,
        borderRadius: 10,
        padding: "0 12px",
        fontSize: 15,
        color: "#FFFFFF",
        outline: "none",
        boxSizing: "border-box",
        boxShadow: focused ? "0 0 0 3px rgba(10,132,255,0.2)" : "none",
        transition: "border-color 0.15s, box-shadow 0.15s",
      }}
    />
  );
}

// ── Add/Edit form modal ───────────────────────────────────────────────────────

function AccountForm({
  form,
  setForm,
  editId,
  error,
  saving,
  onSave,
  onCancel,
}: {
  form: FormData;
  setForm: (f: FormData) => void;
  editId: number | null;
  error: string;
  saving: boolean;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <div style={{
      background: "#2C2C2E",
      borderRadius: 12,
      padding: "20px 16px",
      marginBottom: 32,
    }}>
      <div style={{ ...SF, fontSize: 20, fontWeight: 600, color: "#FFFFFF", marginBottom: 20 }}>
        {editId ? "Edit Account" : "Add Broker Account"}
      </div>

      {error && (
        <div style={{
          ...SF,
          background: "rgba(255,69,58,0.12)",
          border: "1px solid rgba(255,69,58,0.3)",
          borderRadius: 10,
          padding: "10px 14px",
          fontSize: 14,
          color: "#FF453A",
          marginBottom: 16,
        }}>
          {error}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div>
          <div style={{ ...SF, fontSize: 13, color: "rgba(235,235,245,0.6)", marginBottom: 6 }}>Display Name</div>
          <IOSInput value={form.name} onChange={(v) => setForm({ ...form, name: v })} placeholder="e.g. PUPrime Demo" autoFocus />
        </div>
        <div>
          <div style={{ ...SF, fontSize: 13, color: "rgba(235,235,245,0.6)", marginBottom: 6 }}>Account Number</div>
          <IOSInput value={form.account_number} onChange={(v) => setForm({ ...form, account_number: v })} placeholder="e.g. 700074018" />
        </div>
        <div>
          <div style={{ ...SF, fontSize: 13, color: "rgba(235,235,245,0.6)", marginBottom: 6 }}>
            Password{editId ? " (leave blank to keep current)" : ""}
          </div>
          <IOSInput type="password" value={form.password} onChange={(v) => setForm({ ...form, password: v })} placeholder="••••••••" />
        </div>
        <div>
          <div style={{ ...SF, fontSize: 13, color: "rgba(235,235,245,0.6)", marginBottom: 6 }}>Server</div>
          <IOSInput value={form.server} onChange={(v) => setForm({ ...form, server: v })} placeholder="e.g. PUPrime-Demo" />
        </div>

        {/* Demo toggle row */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 0",
        }}>
          <span style={{ ...SF, fontSize: 17, color: "#FFFFFF" }}>Demo Account</span>
          <Toggle value={form.is_demo} onChange={(v) => setForm({ ...form, is_demo: v })} />
        </div>
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 24 }}>
        <button
          onClick={onSave}
          disabled={saving}
          style={{
            ...SF,
            flex: 1,
            height: 44,
            background: "#0A84FF",
            border: "none",
            borderRadius: 12,
            fontSize: 17,
            fontWeight: 600,
            color: "#FFFFFF",
            cursor: saving ? "not-allowed" : "pointer",
            opacity: saving ? 0.6 : 1,
            transition: "opacity 0.15s",
          }}
        >
          {saving ? "Saving…" : editId ? "Update" : "Add Account"}
        </button>
        <button
          onClick={onCancel}
          style={{
            ...SF,
            flex: 1,
            height: 44,
            background: "rgba(120,120,128,0.24)",
            border: "none",
            borderRadius: 12,
            fontSize: 17,
            fontWeight: 600,
            color: "#FFFFFF",
            cursor: "pointer",
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [accounts, setAccounts] = useState<BrokerAccount[]>([]);
  const [botStatus, setBotStatus] = useState<BotStatus>({});
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<FormData>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<number | null>(null);
  const [demoMode, setDemoMode] = useState(false);
  const [logLevel, setLogLevel] = useState("INFO");

  const load = useCallback(() => {
    Promise.all([
      fetch("/api/broker/accounts").then((r) => r.json()).catch(() => []),
      fetch("/api/status").then((r) => r.json()).catch(() => ({})),
    ]).then(([accs, status]) => {
      if (Array.isArray(accs)) setAccounts(accs);
      if (status && typeof status === "object") setBotStatus(status);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const resetForm = () => { setForm(EMPTY_FORM); setEditId(null); setShowForm(false); setError(""); };

  const handleSave = async () => {
    if (!form.name || !form.account_number || !form.server) {
      setError("Name, account number, and server are required."); return;
    }
    if (!editId && !form.password) {
      setError("Password is required for new accounts."); return;
    }
    setSaving(true); setError("");
    try {
      const url = editId ? `/api/broker/accounts/${editId}` : "/api/broker/accounts";
      const method = editId ? "PUT" : "POST";
      const body: Record<string, unknown> = {
        name: form.name, account_number: form.account_number,
        server: form.server, is_demo: form.is_demo,
      };
      if (form.password) body.password = form.password;
      const r = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (!r.ok) { const err = await r.json(); throw new Error(err.error || "Failed to save"); }
      resetForm(); load();
    } catch (e) { setError((e as Error).message); }
    finally { setSaving(false); }
  };

  const handleActivate = async (id: number) => {
    await fetch(`/api/broker/accounts/${id}`, { method: "PATCH" }); load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this broker account?")) return;
    setDeleting(id);
    await fetch(`/api/broker/accounts/${id}`, { method: "DELETE" });
    setDeleting(null); load();
  };

  const handleEdit = (a: BrokerAccount) => {
    setEditId(a.id);
    setForm({ name: a.name, account_number: a.account_number, password: "", server: a.server, is_demo: a.is_demo });
    setShowForm(true);
  };

  const dbColor = botStatus.db === "ok" ? "#30D158" : "#FF453A";

  return (
    <div style={{
      ...SF,
      paddingTop: 20,
      paddingBottom: 40,
      maxWidth: 640,
    }}>
      {/* Page title */}
      <h1 style={{
        fontSize: 34,
        fontWeight: 700,
        color: "#FFFFFF",
        margin: "0 0 32px 0",
        letterSpacing: "-0.02em",
      }}>
        Preferences
      </h1>

      {/* Bot Account section */}
      <Section title="Bot Account">
        <Row label="Broker" value={botStatus.broker || "—"} />
        <Row label="Account" value={botStatus.account_number || "—"} />
        <Row label="Server" value={botStatus.server || "—"} last />
      </Section>

      {/* Broker Accounts section */}
      <Section title="Broker Accounts" footer="The active account is used when the bot next starts. Restart the bot after switching.">
        {loading ? (
          <Row label="Loading…" value="" last />
        ) : accounts.length === 0 ? (
          <Row label="No accounts configured" value="" last valueColor="rgba(235,235,245,0.3)" />
        ) : (
          accounts.map((a, i) => (
            <div key={a.id}>
              <div style={{
                display: "flex",
                alignItems: "center",
                minHeight: 60,
                padding: "10px 16px",
                gap: 12,
              }}>
                {/* Active indicator */}
                <div style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: a.is_active ? "#30D158" : "rgba(120,120,128,0.36)",
                  flexShrink: 0,
                  boxShadow: a.is_active ? "0 0 6px rgba(48,209,88,0.6)" : "none",
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
                    <span style={{ fontSize: 17, color: "#FFFFFF", fontWeight: 500 }}>{a.name}</span>
                    {a.is_active && (
                      <span style={{
                        fontSize: 11,
                        fontWeight: 600,
                        background: "rgba(48,209,88,0.15)",
                        color: "#30D158",
                        border: "1px solid rgba(48,209,88,0.35)",
                        borderRadius: 4,
                        padding: "1px 6px",
                      }}>
                        Active
                      </span>
                    )}
                    <span style={{
                      fontSize: 11,
                      fontWeight: 600,
                      background: a.is_demo ? "rgba(255,159,10,0.15)" : "rgba(255,69,58,0.15)",
                      color: a.is_demo ? "#FF9F0A" : "#FF453A",
                      border: `1px solid ${a.is_demo ? "rgba(255,159,10,0.35)" : "rgba(255,69,58,0.35)"}`,
                      borderRadius: 4,
                      padding: "1px 6px",
                    }}>
                      {a.is_demo ? "Demo" : "Live"}
                    </span>
                  </div>
                  <div style={{ fontSize: 13, color: "rgba(235,235,245,0.4)" }}>
                    {a.server}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                  {!a.is_active && (
                    <button
                      onClick={() => handleActivate(a.id)}
                      style={{
                        ...SF,
                        height: 32,
                        padding: "0 12px",
                        background: "rgba(10,132,255,0.15)",
                        border: "1px solid rgba(10,132,255,0.4)",
                        borderRadius: 8,
                        fontSize: 14,
                        fontWeight: 600,
                        color: "#0A84FF",
                        cursor: "pointer",
                      }}
                    >
                      Activate
                    </button>
                  )}
                  <button
                    onClick={() => handleEdit(a)}
                    style={{
                      ...SF,
                      height: 32,
                      padding: "0 12px",
                      background: "rgba(120,120,128,0.18)",
                      border: "1px solid rgba(84,84,88,0.5)",
                      borderRadius: 8,
                      fontSize: 14,
                      fontWeight: 500,
                      color: "rgba(235,235,245,0.7)",
                      cursor: "pointer",
                    }}
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(a.id)}
                    disabled={deleting === a.id}
                    style={{
                      ...SF,
                      height: 32,
                      padding: "0 12px",
                      background: "rgba(255,69,58,0.1)",
                      border: "1px solid rgba(255,69,58,0.3)",
                      borderRadius: 8,
                      fontSize: 14,
                      fontWeight: 500,
                      color: "#FF453A",
                      cursor: deleting === a.id ? "not-allowed" : "pointer",
                      opacity: deleting === a.id ? 0.5 : 1,
                    }}
                  >
                    {deleting === a.id ? "…" : "Delete"}
                  </button>
                </div>
              </div>
              {i < accounts.length - 1 && (
                <div style={{ height: "0.5px", background: "rgba(84,84,88,0.65)", marginLeft: 16 }} />
              )}
            </div>
          ))
        )}
        {/* Separator before Add button */}
        <div style={{ height: "0.5px", background: "rgba(84,84,88,0.65)", marginLeft: 16 }} />
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          style={{
            ...SF,
            display: "block",
            width: "100%",
            height: 44,
            background: "transparent",
            border: "none",
            borderRadius: 0,
            fontSize: 17,
            fontWeight: 400,
            color: "#0A84FF",
            cursor: "pointer",
            textAlign: "left",
            padding: "0 16px",
          }}
        >
          Add Account
        </button>
      </Section>

      {/* Add/Edit form */}
      {showForm && (
        <AccountForm
          form={form}
          setForm={setForm}
          editId={editId}
          error={error}
          saving={saving}
          onSave={handleSave}
          onCancel={resetForm}
        />
      )}

      {/* Bot Controls section */}
      <Section title="Bot Controls">
        <Row label="Demo Mode" last={false}>
          <Toggle value={demoMode} onChange={setDemoMode} />
        </Row>
        <Row label="Log Level" last>
          <select
            value={logLevel}
            onChange={(e) => setLogLevel(e.target.value)}
            style={{
              ...SF,
              background: "transparent",
              border: "none",
              outline: "none",
              fontSize: 17,
              color: "rgba(235,235,245,0.6)",
              cursor: "pointer",
              appearance: "none",
              paddingRight: 20,
            }}
          >
            {["DEBUG", "INFO", "WARNING", "ERROR"].map((l) => (
              <option key={l} value={l} style={{ background: "#1C1C1E", color: "#FFFFFF" }}>{l}</option>
            ))}
          </select>
          <svg width="8" height="13" viewBox="0 0 8 13" fill="none" style={{ opacity: 0.3, marginLeft: 4 }}>
            <path d="M1 1l6 5.5L1 12" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </Row>
      </Section>

      {/* Dashboard section */}
      <Section title="Dashboard">
        <Row label="Refresh Interval" value="5 seconds" />
        <Row label="Theme" value="iOS Dark" last />
      </Section>

      {/* About section */}
      <Section title="About">
        <Row label="App Version" value={botStatus.version || "—"} />
        <Row label="Bot Version" value={botStatus.bot_version || "—"} />
        <Row
          label="Database"
          value={botStatus.db === "ok" ? "Connected" : botStatus.db || "—"}
          valueColor={dbColor}
          last
        />
      </Section>
    </div>
  );
}
