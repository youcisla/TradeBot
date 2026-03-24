"use client";

import { signIn } from "next-auth/react";
import { FormEvent, useState, useEffect } from "react";
import TerminalInput from "@/components/TerminalInput";

/* LoginInput replaced by shared TerminalInput component */

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState(false);
  const [loading, setLoading]   = useState(false);
  const [isFirstLogin, setIsFirstLogin] = useState<boolean | null>(null);

  useEffect(() => {
    fetch("/api/auth/check")
      .then((r) => r.json())
      .then((data) => setIsFirstLogin(data.firstLogin))
      .catch(() => {});
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(false);
    const res = await signIn("credentials", { username, password, redirect: false });
    if (res?.ok) {
      window.location.href = "/dashboard";
    } else {
      setError(true);
      setLoading(false);
    }
  }

  const disabled = loading || !username || !password;

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "#080808",
    }}>
      <form
        onSubmit={handleSubmit}
        style={{
          background: "#0a0a12",
          border: "1px solid #1c1c28",
          borderTop: "2px solid #00ff88",
          borderRadius: 8,
          padding: "36px 32px",
          width: "100%",
          maxWidth: 340,
          boxSizing: "border-box",
        }}
      >
        {/* Logo / brand */}
        <div style={{ marginBottom: 24 }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 9, fontWeight: 700, letterSpacing: "0.2em",
            textTransform: "uppercase", color: "#607888",
            marginBottom: 4,
          }}>
            NeuralFX
          </div>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 20, fontWeight: 700,
            color: "#00ff88",
            textShadow: "0 0 18px rgba(0,255,136,0.35)",
          }}>
            TRADING BOT
          </div>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10, color: "#607888",
            marginTop: 6, lineHeight: 1.5,
          }}>
            {isFirstLogin
              ? "First login — credentials will create the admin account."
              : "Enter your credentials to continue."}
          </div>
        </div>

        <div style={{ marginBottom: 10 }}>
          <TerminalInput
            type="text"
            value={username}
            onChange={setUsername}
            placeholder="username"
            autoFocus
            autoComplete="username"
          />
        </div>
        <div style={{ marginBottom: 10 }}>
          <TerminalInput
            type="password"
            value={password}
            onChange={setPassword}
            placeholder="password"
            autoComplete="current-password"
          />
        </div>

        {error && (
          <div style={{
            background: "rgba(255,68,85,0.08)",
            border: "1px solid rgba(255,68,85,0.25)",
            borderRadius: 4,
            padding: "7px 10px",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10, color: "#ff4455",
            marginBottom: 10,
          }}>
            Access denied — wrong credentials.
          </div>
        )}

        <button
          type="submit"
          disabled={disabled}
          style={{
            display: "block",
            width: "100%",
            padding: "10px",
            background: disabled ? "rgba(0,255,136,0.03)" : "rgba(0,255,136,0.1)",
            border: `1px solid ${disabled ? "rgba(0,255,136,0.15)" : "rgba(0,255,136,0.35)"}`,
            borderRadius: 4,
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11, fontWeight: 700, letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: disabled ? "rgba(0,255,136,0.25)" : "#00ff88",
            cursor: disabled ? "not-allowed" : "pointer",
            marginTop: 4,
            transition: "background 0.15s, box-shadow 0.15s",
          }}
          onMouseEnter={(e) => {
            if (!disabled) {
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(0,255,136,0.18)";
              (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 0 14px rgba(0,255,136,0.2)";
            }
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background = disabled ? "rgba(0,255,136,0.03)" : "rgba(0,255,136,0.1)";
            (e.currentTarget as HTMLButtonElement).style.boxShadow = "none";
          }}
        >
          {loading
            ? "Authenticating…"
            : isFirstLogin
              ? "Create Account & Login"
              : "Authenticate"}
        </button>
      </form>
    </div>
  );
}
