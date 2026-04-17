import { NextResponse } from "next/server";
import { apiError } from "@/lib/api-errors";

export const dynamic = "force-dynamic";

const CRUCIX_URL = process.env.CRUCIX_URL || "http://localhost:3117";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normalize(raw: any) {
  // VIX
  const vixValue: number = raw?.markets?.vix?.value ?? raw?.vix ?? null;

  // Yield curve inversion — 10Y minus 2Y spread from FRED data
  const fredSeries: Array<{ id: string; value: number }> = raw?.fred ?? [];
  const t10y = fredSeries.find((f) => f.id === "GS10")?.value ?? null;
  const t2y  = fredSeries.find((f) => f.id === "GS2")?.value ?? null;
  const yieldCurveInverted = t10y !== null && t2y !== null ? t10y - t2y < 0 : false;

  // Sweep age in minutes
  const sweepTs: string | null = raw?.meta?.timestamp ?? null;
  const sweepAgeMinutes = sweepTs
    ? Math.floor((Date.now() - new Date(sweepTs).getTime()) / 60_000)
    : null;

  // OSINT sentiment from GDELT tone or Telegram
  const gdeltTone: number | null = raw?.gdelt?.avgTone ?? null;
  let osintSentiment = "neutral";
  if (gdeltTone !== null) {
    if (gdeltTone < -3)      osintSentiment = "bearish";
    else if (gdeltTone > 3)  osintSentiment = "bullish";
  }

  // Risk tier
  let riskTier = "CLEAR";
  if (vixValue !== null) {
    if      (vixValue > 40) riskTier = "FLASH";
    else if (vixValue > 28) riskTier = "PRIORITY";
    else if (vixValue > 18) riskTier = "ROUTINE";
  }

  // Alerts — flatten from GDELT top themes and Telegram urgent
  const alerts: Array<{ tier: string; title: string }> = [];
  const tgUrgent: Array<{ text?: string }> = raw?.tg?.urgent ?? [];
  for (const p of tgUrgent.slice(0, 4)) {
    if (p.text) alerts.push({ tier: "PRIORITY", title: String(p.text).slice(0, 100) });
  }
  const gdeltThemes: Array<{ theme?: string; count?: number }> = raw?.gdelt?.themes ?? [];
  for (const t of gdeltThemes.slice(0, 4)) {
    if (t.theme) alerts.push({ tier: "ROUTINE", title: t.theme });
  }

  // Source count
  const sourceCount: number = raw?.meta?.sourcesOk ?? raw?.meta?.sourcesQueried ?? 27;

  return {
    riskTier,
    vix: vixValue,
    yieldCurveInverted,
    osintSentiment,
    sweepAgeMinutes,
    alerts,
    sourceCount,
  };
}

export async function GET() {
  try {
    const res = await fetch(`${CRUCIX_URL}/api/data`, {
      signal: AbortSignal.timeout(4_000),
      cache: "no-store",
    });
    if (!res.ok) return apiError("CRUCIX_UNAVAILABLE", "Crucix service unavailable", 503);
    const raw = await res.json();
    return NextResponse.json({ available: true, ...normalize(raw) });
  } catch {
    return apiError("CRUCIX_UNAVAILABLE", "Crucix service unavailable", 503);
  }
}
