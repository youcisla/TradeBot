"use client";

import { signIn } from "next-auth/react";
import { FormEvent, useState } from "react";

const SF: React.CSSProperties = {
  fontFamily: `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`,
};

function IOSInput({
  type = "text",
  value,
  onChange,
  placeholder,
  autoFocus,
  autoComplete,
}: {
  type?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
  autoComplete?: string;
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
      autoComplete={autoComplete}
      style={{
        ...SF,
        display: "block",
        width: "100%",
        height: 44,
        background: "rgba(120,120,128,0.36)",
        border: `1px solid ${focused ? "#0A84FF" : "transparent"}`,
        borderRadius: 10,
        padding: "0 14px",
        fontSize: 17,
        color: "#FFFFFF",
        outline: "none",
        boxSizing: "border-box",
        boxShadow: focused ? "0 0 0 3px rgba(10,132,255,0.25)" : "none",
        transition: "border-color 0.15s, box-shadow 0.15s",
      }}
    />
  );
}

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);

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

  async function handleDemo() {
    setLoading(true);
    setError(false);
    const res = await signIn("credentials", { username: "demo", password: "demo", redirect: false });
    if (res?.ok) {
      window.location.href = "/dashboard";
    } else {
      setError(true);
      setLoading(false);
    }
  }

  const submitDisabled = loading || !username || !password;

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "#000000",
      padding: "20px",
    }}>
      <form
        onSubmit={handleSubmit}
        style={{
          width: "100%",
          maxWidth: 360,
          background: "#1C1C1E",
          borderRadius: 20,
          padding: "32px 24px",
          boxSizing: "border-box",
          boxShadow: "0 0 60px rgba(10,132,255,0.12), 0 24px 60px rgba(0,0,0,0.5)",
        }}
      >
        {/* Logo / brand */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{
            ...SF,
            fontSize: 28,
            fontWeight: 700,
            color: "#FFFFFF",
            letterSpacing: "-0.02em",
            marginBottom: 4,
          }}>
            NeuralFX
          </div>
          <div style={{
            ...SF,
            fontSize: 15,
            color: "rgba(235,235,245,0.4)",
            fontWeight: 400,
          }}>
            Trading Intelligence
          </div>
        </div>

        {/* Inputs */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 12 }}>
          <IOSInput
            type="text"
            value={username}
            onChange={setUsername}
            placeholder="Username"
            autoFocus
            autoComplete="username"
          />
          <IOSInput
            type="password"
            value={password}
            onChange={setPassword}
            placeholder="Password"
            autoComplete="current-password"
          />
        </div>

        {/* Error message */}
        {error && (
          <div style={{
            ...SF,
            background: "rgba(255,69,58,0.12)",
            border: "1px solid rgba(255,69,58,0.35)",
            borderRadius: 10,
            padding: "10px 14px",
            fontSize: 14,
            color: "#FF453A",
            textAlign: "center",
            marginBottom: 12,
          }}>
            Incorrect username or password.
          </div>
        )}

        {/* Sign In button */}
        <button
          type="submit"
          disabled={submitDisabled}
          style={{
            ...SF,
            display: "block",
            width: "100%",
            height: 44,
            background: submitDisabled ? "rgba(10,132,255,0.3)" : "#0A84FF",
            border: "none",
            borderRadius: 12,
            fontSize: 17,
            fontWeight: 600,
            color: submitDisabled ? "rgba(255,255,255,0.4)" : "#FFFFFF",
            cursor: submitDisabled ? "not-allowed" : "pointer",
            marginBottom: 10,
            transition: "background 0.15s, color 0.15s",
          }}
          onMouseEnter={(e) => {
            if (!submitDisabled) (e.currentTarget as HTMLButtonElement).style.background = "#0070D8";
          }}
          onMouseLeave={(e) => {
            if (!submitDisabled) (e.currentTarget as HTMLButtonElement).style.background = "#0A84FF";
          }}
        >
          {loading ? "Signing in…" : "Sign In"}
        </button>

        {/* Demo mode button */}
        <button
          type="button"
          onClick={handleDemo}
          disabled={loading}
          style={{
            ...SF,
            display: "block",
            width: "100%",
            height: 44,
            background: "transparent",
            border: "1px solid rgba(84,84,88,0.65)",
            borderRadius: 12,
            fontSize: 17,
            fontWeight: 400,
            color: "rgba(235,235,245,0.5)",
            cursor: loading ? "not-allowed" : "pointer",
            transition: "border-color 0.15s, color 0.15s",
          }}
          onMouseEnter={(e) => {
            if (!loading) {
              (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(84,84,88,1)";
              (e.currentTarget as HTMLButtonElement).style.color = "rgba(235,235,245,0.8)";
            }
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(84,84,88,0.65)";
            (e.currentTarget as HTMLButtonElement).style.color = "rgba(235,235,245,0.5)";
          }}
        >
          Demo Mode
        </button>
      </form>
    </div>
  );
}
