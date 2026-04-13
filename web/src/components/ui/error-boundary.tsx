"use client";

import { Component, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div
          className="flex flex-col items-center justify-center gap-4 py-20 text-center"
          style={{ background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)" }}
        >
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 40, color: "var(--negative)" }}
          >
            error
          </span>
          <div className="flex flex-col gap-1">
            <span
              style={{ color: "var(--text-1)", fontFamily: "var(--font-ui)", fontSize: 14, fontWeight: 700 }}
            >
              Something went wrong
            </span>
            <span
              style={{ color: "var(--text-3)", fontFamily: "var(--font-ui)", fontSize: 12 }}
            >
              {this.state.error?.message ?? "An unexpected error occurred"}
            </span>
          </div>
          <button
            onClick={() => this.setState({ hasError: false })}
            className="rounded px-4 py-2 text-sm font-semibold transition-all cursor-pointer"
            style={{
              background: "var(--bg-3)",
              border: "1px solid var(--border)",
              color: "var(--text-1)",
              fontFamily: "var(--font-ui)",
            }}
          >
            Retry
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}