"use client";

import { useAppShell } from "@/components/AppShell";
import React, { useState, useEffect } from "react";

const SYMBOLS = ['EURUSD', 'XAUUSD', 'BTCUSD'];

interface Ticker { symbol: string; price: string; change: number; }

async function fetchLiveTickers(): Promise<Ticker[]> {
  try {
    const results = await Promise.all(
      SYMBOLS.map(async (symbol) => {
        const res = await fetch(`/api/candles?symbol=${symbol}&timeframe=M1&count=2`);
        if (!res.ok) return { symbol, price: '—', change: 0 };
        const data = await res.json();
        if (!data.candles || data.candles.length < 2) return { symbol, price: '—', change: 0 };
        const curr = data.candles[data.candles.length - 1];
        const prev = data.candles[data.candles.length - 2];
        const currClose = curr.c;
        const prevClose = prev.c;
        const changePct = prevClose > 0 ? ((currClose - prevClose) / prevClose * 100) : 0;
        return {
          symbol,
          price: currClose >= 100 ? currClose.toFixed(2) : currClose >= 1 ? currClose.toFixed(4) : currClose.toFixed(5),
          change: parseFloat(changePct.toFixed(2)),
        };
      })
    );
    return results;
  } catch {
    return SYMBOLS.map(s => ({ symbol: s, price: '—', change: 0 }));
  }
}

export default function DashHeader() {
  const { status, isRunning } = useAppShell();
  const [tickers, setTickers] = useState<Ticker[]>([
    { symbol: 'EURUSD', price: '—', change: 0 },
    { symbol: 'XAUUSD', price: '—', change: 0 },
    { symbol: 'BTCUSD', price: '—', change: 0 },
  ]);

  useEffect(() => {
    fetchLiveTickers().then(setTickers);
    const interval = setInterval(async () => {
      setTickers(prev => {
        fetchLiveTickers().then(setTickers);
        return prev;
      });
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  const equity = status ? Number(status.equity) : null;
  
  let stateText = "—";
  let stateIcon = "✗";
  let stateColor = "text-text-3";
  if (status) {
    if (isRunning) {
      stateText = "LIVE";
      stateIcon = "●";
      stateColor = "text-cyan animate-pulse";
    } else if (status.state === "paused") {
      stateText = "PAUSED";
      stateIcon = "⏸";
      stateColor = "text-orange";
    } else {
      stateText = "STOPPED";
      stateIcon = "✗";
      stateColor = "text-red";
    }
  }

  return (
    <header className="fixed top-0 left-0 right-0 h-[52px] z-[100] bg-bg-2 border-b border-border flex items-center justify-between px-4">
      {/* Left */}
      <div className="flex items-center gap-2">
        <span className="text-gold font-mono font-bold">◆ NeuralFX</span>
      </div>

      {/* Center Tickers */}
      <div className="hidden md:flex items-center gap-6 font-mono text-sm">
        {tickers.map(t => {
          const isUp = t.change >= 0;
          return (
            <div key={t.symbol} className="flex flex-row items-center gap-2">
              <span className="text-text-2">{t.symbol}</span>
              <span className="text-text-1">{t.price}</span>
              <span className={isUp ? 'text-gold' : 'text-red'}>
                {isUp ? '▲' : '▼'}{Math.abs(t.change).toFixed(2)}%
              </span>
            </div>
          );
        })}
      </div>

      {/* Right */}
      <div className="flex items-center gap-4">
        {/* Status Badge */}
        <div className="flex items-center gap-2 bg-bg-3 border border-border px-3 py-1 rounded-pill">
          <span className={`font-mono text-[10px] ${stateColor}`}>{stateIcon}</span>
          <span className="font-ui text-xs font-bold uppercase tracking-wider text-text-1">
            {stateText}
          </span>
        </div>
        
        {equity !== null && (
          <div className="font-mono text-sm text-text-1">
             {equity.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 })}
          </div>
        )}

        {/* Telegram icon */}
        <button className="text-text-2 hover:text-cyan transition-colors">
          <span className="material-symbols-outlined text-[20px]">send</span>
        </button>
      </div>
    </header>
  );
}
