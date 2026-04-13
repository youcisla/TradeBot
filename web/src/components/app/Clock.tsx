"use client";

import { useEffect, useState } from "react";

const TIMEZONE = "Europe/Paris";

export function Clock() {
  const [tick, setTick] = useState("—");

  useEffect(() => {
    function update() {
      setTick(
        new Date().toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
          timeZone: TIMEZONE,
        })
      );
    }
    update();
    const id = setInterval(update, 1_000);
    return () => clearInterval(id);
  }, []);

  return (
    <span
      className="font-mono tabular-nums"
      style={{ color: "var(--text-2)", fontFamily: "var(--font-mono)", fontSize: 12 }}
    >
      {tick}
    </span>
  );
}
