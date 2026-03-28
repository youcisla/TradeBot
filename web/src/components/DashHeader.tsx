"use client";

import { useEffect, useState } from "react";
import { nowParis } from "@/lib/time";

export default function DashHeader() {
  const [localTime, setLocalTime] = useState("--:--:--");

  useEffect(() => {
    const tick = () => setLocalTime(nowParis());
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="bg-surface-container-lowest fixed top-0 left-0 w-full z-50">
      <div className="flex justify-between items-center px-4 py-2 w-full">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-primary-fixed" style={{ fontSize: 18 }}>
            language
          </span>
          <span className="text-primary-fixed font-bold tracking-widest text-xl uppercase">
            NEURALFX
          </span>
        </div>
        <div className="font-mono uppercase tracking-tighter text-sm text-primary">
          {localTime}
        </div>
      </div>
      <div className="bg-surface-container-low h-px w-full" />
    </header>
  );
}
