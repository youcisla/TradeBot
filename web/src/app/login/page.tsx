"use client";

import { signIn } from "next-auth/react";
import { FormEvent, useState } from "react";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isFirstLogin, setIsFirstLogin] = useState<boolean | null>(null);

  // Check if this is the first login (no users exist)
  useState(() => {
    fetch("/api/auth/check")
      .then((r) => r.json())
      .then((data) => setIsFirstLogin(data.firstLogin))
      .catch(() => {});
  });

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(false);
    const res = await signIn("credentials", {
      username,
      password,
      redirect: false,
    });
    if (res?.ok) {
      window.location.href = "/dashboard";
    } else {
      setError(true);
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-terminal">
      <form
        onSubmit={handleSubmit}
        className="border border-terminal-border rounded bg-terminal-surface p-8 w-full max-w-sm"
      >
        <div className="text-matrix text-lg font-bold mb-1 cursor-blink">
          TRADING BOT
        </div>
        <div className="text-matrix-dim text-xs mb-6">
          {isFirstLogin
            ? "First login — your credentials will create the admin account."
            : "Enter your credentials to continue."}
        </div>

        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="username"
          autoFocus
          autoComplete="username"
          className="w-full bg-terminal border border-terminal-border rounded px-3 py-2 text-matrix text-sm font-mono focus:outline-none focus:border-matrix mb-3"
        />

        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="password"
          autoComplete="current-password"
          className="w-full bg-terminal border border-terminal-border rounded px-3 py-2 text-matrix text-sm font-mono focus:outline-none focus:border-matrix mb-4"
        />

        {error && (
          <div className="text-red-500 text-xs mb-3">
            Access denied — wrong credentials.
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !username || !password}
          className="w-full border border-matrix text-matrix rounded py-2 text-xs font-bold uppercase hover:bg-matrix hover:text-black transition-colors disabled:opacity-40"
        >
          {loading
            ? "Authenticating…"
            : isFirstLogin
              ? "CREATE ACCOUNT & LOGIN"
              : "AUTHENTICATE"}
        </button>
      </form>
    </div>
  );
}
