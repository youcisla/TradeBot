"use client";

import { useEffect, useState, useCallback } from "react";

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

export default function SettingsPage() {
  const [accounts, setAccounts] = useState<BrokerAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<FormData>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    fetch("/api/broker/accounts")
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) setAccounts(data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

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
      const url = editId
        ? `/api/broker/accounts/${editId}`
        : "/api/broker/accounts";
      const method = editId ? "PUT" : "POST";
      const body: Record<string, unknown> = {
        name: form.name,
        account_number: form.account_number,
        server: form.server,
        is_demo: form.is_demo,
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
    await fetch(`/api/broker/accounts/${id}`, { method: "DELETE" });
    load();
  };

  const handleEdit = (a: BrokerAccount) => {
    setEditId(a.id);
    setForm({
      name: a.name,
      account_number: a.account_number,
      password: "",
      server: a.server,
      is_demo: a.is_demo,
    });
    setShowForm(true);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-matrix text-xl font-bold">
        &gt; BROKER ACCOUNTS
      </h1>
      <p className="text-matrix-dim text-sm">
        Add your demo or live broker accounts. The <strong>active</strong>{" "}
        account is used when the bot next starts. Restart the bot after
        switching accounts.
      </p>

      {/* Account list */}
      {loading ? (
        <p className="text-matrix-dim text-sm">Loading…</p>
      ) : accounts.length === 0 ? (
        <div className="border border-terminal-border rounded p-6 bg-terminal-surface text-center">
          <p className="text-matrix-dim mb-4">No broker accounts configured.</p>
          <p className="text-matrix-dim text-xs">
            The bot is using credentials from .env as fallback.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {accounts.map((a) => (
            <div
              key={a.id}
              className={`border rounded p-4 bg-terminal-surface flex flex-wrap items-center gap-4 text-sm ${
                a.is_active
                  ? "border-matrix"
                  : "border-terminal-border"
              }`}
            >
              <div className="flex-1 min-w-[200px]">
                <div className="flex items-center gap-2">
                  <span className="text-matrix font-bold">{a.name}</span>
                  {a.is_active && (
                    <span className="text-xs bg-matrix/20 text-matrix px-2 py-0.5 rounded">
                      ACTIVE
                    </span>
                  )}
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      a.is_demo
                        ? "bg-yellow-500/20 text-yellow-400"
                        : "bg-red-500/20 text-red-400"
                    }`}
                  >
                    {a.is_demo ? "DEMO" : "LIVE"}
                  </span>
                </div>
                <div className="text-matrix-dim mt-1">
                  Account: {a.account_number} · Server: {a.server}
                </div>
                {a.last_connected && (
                  <div className="text-matrix-dim text-xs mt-0.5">
                    Last connected: {new Date(a.last_connected).toLocaleString()}
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                {!a.is_active && (
                  <button
                    onClick={() => handleActivate(a.id)}
                    className="px-3 py-1 border border-matrix text-matrix rounded hover:bg-matrix/20 text-xs"
                  >
                    ACTIVATE
                  </button>
                )}
                <button
                  onClick={() => handleEdit(a)}
                  className="px-3 py-1 border border-terminal-border text-matrix-dim rounded hover:bg-terminal-border text-xs"
                >
                  EDIT
                </button>
                <button
                  onClick={() => handleDelete(a.id)}
                  className="px-3 py-1 border border-red-500/50 text-red-400 rounded hover:bg-red-500/20 text-xs"
                >
                  DELETE
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add / Edit form */}
      {!showForm ? (
        <button
          onClick={() => {
            resetForm();
            setShowForm(true);
          }}
          className="px-4 py-2 border border-matrix text-matrix rounded hover:bg-matrix/20 text-sm"
        >
          + ADD ACCOUNT
        </button>
      ) : (
        <div className="border border-terminal-border rounded p-6 bg-terminal-surface space-y-4">
          <h2 className="text-matrix font-bold text-sm">
            {editId ? "EDIT ACCOUNT" : "NEW BROKER ACCOUNT"}
          </h2>

          {error && (
            <p className="text-red-400 text-xs">{error}</p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="block">
              <span className="text-matrix-dim text-xs">DISPLAY NAME</span>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. PUPrime Demo"
                className="mt-1 w-full bg-terminal border border-terminal-border rounded px-3 py-2 text-matrix text-sm focus:border-matrix outline-none"
              />
            </label>
            <label className="block">
              <span className="text-matrix-dim text-xs">ACCOUNT NUMBER</span>
              <input
                type="text"
                value={form.account_number}
                onChange={(e) =>
                  setForm({ ...form, account_number: e.target.value })
                }
                placeholder="e.g. 700074018"
                className="mt-1 w-full bg-terminal border border-terminal-border rounded px-3 py-2 text-matrix text-sm focus:border-matrix outline-none"
              />
            </label>
            <label className="block">
              <span className="text-matrix-dim text-xs">
                PASSWORD{editId ? " (leave blank to keep)" : ""}
              </span>
              <input
                type="password"
                value={form.password}
                onChange={(e) =>
                  setForm({ ...form, password: e.target.value })
                }
                placeholder="••••••••"
                className="mt-1 w-full bg-terminal border border-terminal-border rounded px-3 py-2 text-matrix text-sm focus:border-matrix outline-none"
              />
            </label>
            <label className="block">
              <span className="text-matrix-dim text-xs">SERVER</span>
              <input
                type="text"
                value={form.server}
                onChange={(e) =>
                  setForm({ ...form, server: e.target.value })
                }
                placeholder="e.g. PUPrime-Demo"
                className="mt-1 w-full bg-terminal border border-terminal-border rounded px-3 py-2 text-matrix text-sm focus:border-matrix outline-none"
              />
            </label>
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_demo}
              onChange={(e) =>
                setForm({ ...form, is_demo: e.target.checked })
              }
              className="accent-[var(--matrix)]"
            />
            <span className="text-matrix-dim">Demo account</span>
          </label>

          <div className="flex gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-matrix/20 border border-matrix text-matrix rounded hover:bg-matrix/30 text-sm disabled:opacity-50"
            >
              {saving ? "SAVING…" : editId ? "UPDATE" : "ADD ACCOUNT"}
            </button>
            <button
              onClick={resetForm}
              className="px-4 py-2 border border-terminal-border text-matrix-dim rounded hover:bg-terminal-border text-sm"
            >
              CANCEL
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
