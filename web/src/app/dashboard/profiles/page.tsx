"use client";

import { useState, FormEvent } from "react";
import { useProfiles } from "@/lib/swr";
import { Sdot } from "@/components/ui/chip";

const SF: React.CSSProperties = {
  fontFamily: `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`,
};

interface ProfileCardProps {
  profile: {
    id: number;
    profile_label: string;
    account_number: string;
    server: string;
    is_demo: boolean;
    is_active: boolean;
  };
  onActivate: (id: number) => void;
  onDelete: (id: number) => void;
}

function ProfileCard({ profile, onActivate, onDelete }: ProfileCardProps) {
  const [confirming, setConfirming] = useState(false);

  return (
    <div
      style={{
        ...SF,
        background: "var(--bg-secondary)",
        border: `1px solid ${profile.is_active ? "var(--accent)" : "var(--border)"}`,
        borderRadius: 14,
        padding: "16px 18px",
        display: "flex",
        alignItems: "center",
        gap: 16,
        transition: "border-color 0.15s",
      }}
    >
      <Sdot tone={profile.is_active ? "pos" : "neutral"} />
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)", marginBottom: 2 }}>
          {profile.profile_label}
        </div>
        <div style={{ fontSize: 13, color: "var(--text-secondary)", fontFamily: "monospace" }}>
          {profile.account_number} · {profile.server}
          <span style={{
            marginLeft: 8,
            padding: "1px 7px",
            borderRadius: 6,
            background: profile.is_demo ? "rgba(10,132,255,0.18)" : "rgba(48,209,88,0.18)",
            color: profile.is_demo ? "#0A84FF" : "#30D158",
            fontSize: 11,
            fontWeight: 600,
          }}>
            {profile.is_demo ? "DEMO" : "LIVE"}
          </span>
        </div>
      </div>
      {!profile.is_active && (
        <>
          {confirming ? (
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => { onActivate(profile.id); setConfirming(false); }}
                style={{ ...SF, fontSize: 13, fontWeight: 600, color: "#30D158", background: "rgba(48,209,88,0.12)", border: "1px solid rgba(48,209,88,0.3)", borderRadius: 8, padding: "6px 14px", cursor: "pointer" }}
              >
                Confirm
              </button>
              <button
                onClick={() => setConfirming(false)}
                style={{ ...SF, fontSize: 13, color: "var(--text-secondary)", background: "transparent", border: "none", cursor: "pointer" }}
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirming(true)}
              style={{ ...SF, fontSize: 13, fontWeight: 500, color: "#0A84FF", background: "transparent", border: "1px solid rgba(10,132,255,0.35)", borderRadius: 8, padding: "6px 14px", cursor: "pointer" }}
            >
              Activate
            </button>
          )}
        </>
      )}
      <button
        onClick={() => onDelete(profile.id)}
        style={{ ...SF, fontSize: 12, color: "rgba(255,69,58,0.7)", background: "transparent", border: "none", cursor: "pointer", padding: "4px 8px" }}
        title="Delete profile"
      >
        ✕
      </button>
    </div>
  );
}

interface NewProfileFormProps {
  onSubmit: (data: { profile_label: string; account_number: string; server: string; investor_password: string; is_demo: boolean }) => void;
  onCancel: () => void;
}

function NewProfileForm({ onSubmit, onCancel }: NewProfileFormProps) {
  const [label, setLabel] = useState("");
  const [account, setAccount] = useState("");
  const [server, setServer] = useState("");
  const [password, setPassword] = useState("");
  const [isDemo, setIsDemo] = useState(true);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!label || !account || !server || !password) return;
    onSubmit({ profile_label: label, account_number: account, server, investor_password: password, is_demo: isDemo });
  }

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        ...SF,
        background: "var(--bg-secondary)",
        border: "1px solid var(--accent)",
        borderRadius: 14,
        padding: "20px 18px",
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
        New Broker Profile
      </div>
      <input
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        placeholder="Profile label (e.g. PU Prime Live)"
        style={inputStyle}
      />
      <input
        value={account}
        onChange={(e) => setAccount(e.target.value)}
        placeholder="Account number"
        style={inputStyle}
      />
      <input
        value={server}
        onChange={(e) => setServer(e.target.value)}
        placeholder="Server (e.g. PU Prime-Server)"
        style={inputStyle}
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Investor password"
        style={inputStyle}
      />
      <div style={{ display: "flex", gap: 10 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--text-secondary)", cursor: "pointer" }}>
          <input type="radio" checked={isDemo} onChange={() => setIsDemo(true)} />
          Demo
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--text-secondary)", cursor: "pointer" }}>
          <input type="radio" checked={!isDemo} onChange={() => setIsDemo(false)} />
          Live
        </label>
      </div>
      <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
        <button
          type="submit"
          style={{ ...SF, flex: 1, height: 38, background: "#0A84FF", border: "none", borderRadius: 10, fontSize: 14, fontWeight: 600, color: "#fff", cursor: "pointer" }}
        >
          Save Profile
        </button>
        <button
          type="button"
          onClick={onCancel}
          style={{ ...SF, flex: 1, height: 38, background: "transparent", border: "1px solid var(--border)", borderRadius: 10, fontSize: 14, color: "var(--text-secondary)", cursor: "pointer" }}
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

const inputStyle: React.CSSProperties = {
  ...SF,
  height: 40,
  background: "var(--bg-tertiary)",
  border: "1px solid var(--border)",
  borderRadius: 9,
  padding: "0 12px",
  fontSize: 14,
  color: "var(--text-primary)",
  outline: "none",
  boxSizing: "border-box",
};

interface ProfilesPageProps {
  sessionToken: string;
  onBack: () => void;
}

export default function ProfilesPage({ sessionToken, onBack }: ProfilesPageProps) {
  const { data: profiles = [], mutate } = useProfiles(sessionToken);
  const [showNewForm, setShowNewForm] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  async function handleActivate(id: number) {
    try {
      const res = await fetch("http://127.0.0.1:8001/api/auth/profiles/activate", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
        body: JSON.stringify({ profile_id: id }),
      });
      if (res.ok) mutate();
    } catch { /* ignore */ }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this profile? This cannot be undone.")) return;
    setDeletingId(id);
    try {
      await fetch(`http://127.0.0.1:8001/api/auth/profiles/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${sessionToken}` },
      });
      mutate();
    } catch { /* ignore */ }
    finally { setDeletingId(null); }
  }

  async function handleCreate(data: { profile_label: string; account_number: string; server: string; investor_password: string; is_demo: boolean }) {
    try {
      const res = await fetch("http://127.0.0.1:8001/api/auth/profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        mutate();
        setShowNewForm(false);
      }
    } catch { /* ignore */ }
  }

  return (
    <div style={{ ...SF, padding: "0 0 40px", maxWidth: 540 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 28 }}>
        <button onClick={onBack} style={{ ...SF, fontSize: 22, color: "var(--text-secondary)", background: "transparent", border: "none", cursor: "pointer", padding: "4px 8px", lineHeight: 1 }}>←</button>
        <div>
          <div style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)" }}>Broker Profiles</div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>Manage your MT5 connection profiles</div>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
        {profiles.map((p) => (
          <ProfileCard
            key={p.id}
            profile={p}
            onActivate={handleActivate}
            onDelete={handleDelete}
          />
        ))}
      </div>

      {showNewForm ? (
        <NewProfileForm onSubmit={handleCreate} onCancel={() => setShowNewForm(false)} />
      ) : (
        <button
          onClick={() => setShowNewForm(true)}
          style={{ ...SF, width: "100%", height: 44, background: "rgba(10,132,255,0.1)", border: "1px dashed rgba(10,132,255,0.4)", borderRadius: 12, fontSize: 14, fontWeight: 500, color: "#0A84FF", cursor: "pointer" }}
        >
          + Add New Profile
        </button>
      )}

      <div style={{ marginTop: 24, padding: "12px 16px", background: "rgba(255,179,0,0.08)", border: "1px solid rgba(255,179,0,0.25)", borderRadius: 10, fontSize: 13, color: "rgba(255,200,80,0.85)", lineHeight: 1.5 }}>
        <strong>Forgot password?</strong> Re-enter your MT5 investor password to unlock. Credentials are encrypted locally — the bot never stores them in plaintext.
      </div>
    </div>
  );
}