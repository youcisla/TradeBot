"use client";

import { signIn } from "next-auth/react";
import { FormEvent, useState } from "react";

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(false);
    const res = await signIn("credentials", {
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
          Enter dashboard password to continue.
        </div>

        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="password"
          autoFocus
          className="w-full bg-terminal border border-terminal-border rounded px-3 py-2 text-matrix text-sm font-mono focus:outline-none focus:border-matrix mb-4"
        />

        {error && (
          <div className="text-red-500 text-xs mb-3">
            Access denied — wrong password.
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full border border-matrix text-matrix rounded py-2 text-xs font-bold uppercase hover:bg-matrix hover:text-black transition-colors disabled:opacity-40"
        >
          {loading ? "Authenticating…" : "AUTHENTICATE"}
        </button>
      </form>
    </div>
  );
}
