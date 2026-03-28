"use client";

import { useEffect, useState, useCallback } from "react";
import TerminalInput from "@/components/TerminalInput";

// ── Types ─────────────────────────────────────────────────────────────────────

interface BrokerAccount {
  id: number; name: string; account_number: string;
  server: string; is_demo: boolean; is_active: boolean;
  created_at: string; last_connected: string | null;
}

interface FormData {
  name: string; account_number: string; password: string;
  server: string; is_demo: boolean;
}

const EMPTY_FORM: FormData = {
  name: "", account_number: "", password: "", server: "", is_demo: true,
};

// ── Sub-components ────────────────────────────────────────────────────────────

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-[9px] font-bold tracking-[0.14em] uppercase text-outline">{label}</span>
        {hint && <span className="text-[9px] text-outline">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [accounts, setAccounts] = useState<BrokerAccount[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editId,   setEditId]   = useState<number | null>(null);
  const [form,     setForm]     = useState<FormData>(EMPTY_FORM);
  const [saving,   setSaving]   = useState(false);
  const [error,    setError]    = useState("");
  const [deleting, setDeleting] = useState<number | null>(null);

  const load = useCallback(() => {
    fetch("/api/broker/accounts")
      .then((r) => r.json())
      .then((data) => { if (Array.isArray(data)) setAccounts(data); })
      .catch(() => {})
      .finally(() => setLoading(false));
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
      const url    = editId ? `/api/broker/accounts/${editId}` : "/api/broker/accounts";
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

  return (
    <div className="flex flex-col gap-6 mt-6">

      {/* ── Page Header ── */}
      <div className="border-l-4 border-primary-fixed pl-6 py-2 bg-surface-container-low">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-primary-fixed text-[10px] font-bold tracking-[0.2em] uppercase">CONFIGURATION</span>
          <span className="w-2 h-2 rounded-full bg-primary-fixed" />
        </div>
        <h1 className="text-3xl md:text-5xl font-extrabold tracking-tighter uppercase mb-2">
          Settings
        </h1>
        <p className="text-on-surface-variant text-sm font-mono">
          The <span className="text-primary-fixed font-bold">active</span> account is used when the bot next starts.
          Restart the bot after switching accounts.
        </p>
      </div>

      {/* ── Account List ── */}
      {loading ? (
        <div className="text-[11px] text-outline py-6 tracking-widest">Connecting to broker database…</div>
      ) : accounts.length === 0 ? (
        <div className="bg-surface-container-low border border-outline-variant/10 p-8 text-center">
          <div className="text-[11px] text-on-surface-variant mb-2">No broker accounts configured.</div>
          <div className="text-[9px] text-outline">Bot is using credentials from .env as fallback</div>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {accounts.map((a) => (
            <div
              key={a.id}
              className="bg-surface-container-low border border-outline-variant/10 flex flex-wrap items-center gap-4 p-4"
              style={{
                borderLeftWidth: 3,
                borderLeftColor: a.is_active ? "#00fd87" : "#494847",
              }}
            >
              {/* Info */}
              <div className="flex-1 min-w-[220px]">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-sm font-bold text-on-surface">{a.name}</span>
                  {a.is_active && (
                    <span className="text-[8px] font-bold px-2 py-0.5 border text-primary-fixed border-primary-fixed/30 bg-primary-fixed/10">
                      ACTIVE
                    </span>
                  )}
                  <span
                    className="text-[8px] font-bold px-2 py-0.5 border"
                    style={{
                      color: a.is_demo ? "#ffb86c" : "#ff716c",
                      background: a.is_demo ? "rgba(255,184,108,0.1)" : "rgba(255,113,108,0.1)",
                      borderColor: a.is_demo ? "rgba(255,184,108,0.25)" : "rgba(255,113,108,0.25)",
                    }}
                  >
                    {a.is_demo ? "DEMO" : "LIVE"}
                  </span>
                </div>
                <div className="text-[10px] text-outline">
                  Account: <span className="text-on-surface-variant">{a.account_number}</span>
                  {" · "}
                  Server: <span className="text-on-surface-variant">{a.server}</span>
                </div>
                {a.last_connected && (
                  <div className="text-[9px] text-outline mt-1">
                    Last connected: {new Date(a.last_connected).toLocaleString()}
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                {!a.is_active && (
                  <button
                    onClick={() => handleActivate(a.id)}
                    className="text-[9px] font-bold px-3 py-1.5 border border-primary-fixed/40 text-primary-fixed bg-primary-fixed/10 hover:bg-primary-fixed/20 duration-0 tracking-widest"
                  >
                    ACTIVATE
                  </button>
                )}
                <button
                  onClick={() => handleEdit(a)}
                  className="text-[9px] font-bold px-3 py-1.5 border border-secondary/40 text-secondary bg-secondary/10 hover:bg-secondary/20 duration-0 tracking-widest"
                >
                  EDIT
                </button>
                <button
                  onClick={() => handleDelete(a.id)}
                  disabled={deleting === a.id}
                  className="text-[9px] font-bold px-3 py-1.5 border border-error/40 text-error bg-error/10 hover:bg-error/20 duration-0 tracking-widest disabled:opacity-40"
                >
                  {deleting === a.id ? "…" : "DELETE"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Add Button / Form ── */}
      {!showForm ? (
        <div>
          <button
            onClick={() => { resetForm(); setShowForm(true); }}
            className="text-[11px] font-bold px-5 py-2 border border-primary-fixed/30 text-primary-fixed bg-primary-fixed/8 hover:bg-primary-fixed/15 duration-0 tracking-widest uppercase"
          >
            + ADD ACCOUNT
          </button>
        </div>
      ) : (
        <div className="bg-surface-container-low border border-outline-variant/10 border-t-2 border-t-primary-fixed p-6">
          {/* Form Header */}
          <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-primary-fixed mb-5">
            {editId ? "Edit Broker Account" : "New Broker Account"}
          </div>

          {/* Error */}
          {error && (
            <div className="bg-error/8 border border-error/25 p-3 mb-5 text-[10px] text-error">
              {error}
            </div>
          )}

          {/* Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
            <Field label="Display Name">
              <TerminalInput
                value={form.name}
                onChange={(v) => setForm({ ...form, name: v })}
                placeholder="e.g. PUPrime Demo"
                accent="#00fd87"
              />
            </Field>
            <Field label="Account Number">
              <TerminalInput
                value={form.account_number}
                onChange={(v) => setForm({ ...form, account_number: v })}
                placeholder="e.g. 700074018"
                accent="#00fd87"
              />
            </Field>
            <Field label="Password" hint={editId ? "(leave blank to keep current)" : undefined}>
              <TerminalInput
                type="password"
                value={form.password}
                onChange={(v) => setForm({ ...form, password: v })}
                placeholder="••••••••"
                accent="#00fd87"
              />
            </Field>
            <Field label="Server">
              <TerminalInput
                value={form.server}
                onChange={(v) => setForm({ ...form, server: v })}
                placeholder="e.g. PUPrime-Demo"
                accent="#00fd87"
              />
            </Field>
          </div>

          {/* Demo Toggle */}
          <div
            className="flex items-center gap-3 cursor-pointer mb-6 select-none w-fit"
            onClick={() => setForm({ ...form, is_demo: !form.is_demo })}
          >
            <div
              className="relative w-9 h-5 border"
              style={{
                background: form.is_demo ? "rgba(255,184,108,0.15)" : "transparent",
                borderColor: form.is_demo ? "rgba(255,184,108,0.4)" : "#494847",
              }}
            >
              <div
                className="absolute top-0.5 w-3.5 h-3.5"
                style={{
                  left: form.is_demo ? "calc(100% - 16px)" : "2px",
                  background: form.is_demo ? "#ffb86c" : "#494847",
                  transition: "left 0.15s, background 0.15s",
                }}
              />
            </div>
            <span
              className="text-[10px] tracking-[0.04em]"
              style={{ color: form.is_demo ? "#ffb86c" : "#494847" }}
            >
              {form.is_demo ? "DEMO account" : "LIVE account"}
            </span>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="text-[11px] font-bold px-5 py-2 border border-primary-fixed/35 text-primary-fixed bg-primary-fixed/10 hover:bg-primary-fixed/18 duration-0 tracking-widest disabled:opacity-40"
            >
              {saving ? "SAVING…" : editId ? "UPDATE" : "ADD ACCOUNT"}
            </button>
            <button
              onClick={resetForm}
              className="text-[11px] font-bold px-5 py-2 border border-outline-variant/30 text-outline hover:text-on-surface-variant hover:border-outline duration-0 tracking-widest"
            >
              CANCEL
            </button>
          </div>
        </div>
      )}

      {/* ── Connection Notes ── */}
      <div className="bg-surface-container-low border border-outline-variant/10 border-l-4 border-l-secondary p-5">
        <div className="text-[9px] font-bold tracking-[0.14em] uppercase text-secondary mb-4">
          Connection Notes
        </div>
        <div className="flex flex-col gap-2.5 text-[11px] text-on-surface-variant">
          {[
            ["Activation",  "Switch accounts via ACTIVATE — takes effect on next bot restart"],
            ["Password",    "Stored encrypted in the local database, never transmitted externally"],
            ["Demo → Live", "Always validate strategy on demo before enabling a live account"],
            ["Fallback",    "If no account is active, the bot reads MT5_LOGIN / MT5_PASSWORD from .env"],
          ].map(([label, text]) => (
            <div key={label} className="flex gap-3">
              <span className="text-outline shrink-0 w-20">{label}</span>
              <span>{text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
