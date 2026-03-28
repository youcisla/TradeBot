"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Line } from "@react-three/drei";
import { useRef, useMemo, useState, useEffect, useCallback } from "react";
import * as THREE from "three";

// ── Types ─────────────────────────────────────────────────────────────────

interface MarketHub {
  name:       string;
  lat:        number;
  lon:        number;
  openHour:   number;   // UTC
  closeHour:  number;   // UTC
  color:      string;
}

interface LiveTrade {
  id:          string;
  symbol:      string;
  direction:   string;  // BUY | SELL
  entry_price: number;
  pnl:         number;
  status:      string;
  open_time:   string;
  hub:         string;  // resolved hub name
}

// ── Market hub definitions ─────────────────────────────────────────────────

const HUBS: MarketHub[] = [
  { name: "London",    lat: 51.5,   lon:  -0.1,  openHour:  8, closeHour: 16, color: "#00d2fd" },
  { name: "New York",  lat: 40.7,   lon: -74.0,  openHour: 13, closeHour: 21, color: "#e966ff" },
  { name: "Tokyo",     lat: 35.7,   lon: 139.7,  openHour:  0, closeHour:  9, color: "#ffb86c" },
  { name: "Sydney",    lat: -33.9,  lon: 151.2,  openHour: 22, closeHour:  6, color: "#00fd87" },
  { name: "Frankfurt", lat: 50.1,   lon:   8.7,  openHour:  7, closeHour: 15, color: "#ffd700" },
  { name: "Zurich",    lat: 47.4,   lon:   8.5,  openHour:  7, closeHour: 15, color: "#ff716c" },
];

// ── Symbol → primary hub mapping ──────────────────────────────────────────
// Every forex pair has one "primary" hub where it's most actively traded.

const SYMBOL_HUB: Record<string, string> = {
  // EUR pairs → London / Frankfurt
  EURUSD: "London", EURGBP: "London",
  EURCHF: "Zurich", EURCAD: "London", EURAUD: "London", EURNZD: "London",
  EURSGD: "Frankfurt", EURHKD: "Frankfurt", EURMXN: "Frankfurt",
  // GBP pairs → London
  GBPUSD: "London", GBPCAD: "London",
  GBPCHF: "London", GBPAUD: "London", GBPNZD: "London",
  // USD pairs → New York
  USDCAD: "New York", USDCHF: "New York", USDHKD: "New York",
  USDSGD: "New York", USDMXN: "New York", USDCNH: "New York",
  USDSEK: "New York", USDNOK: "New York", USDDKK: "New York",
  // JPY pairs → Tokyo (primary)
  USDJPY: "Tokyo", CADJPY: "Tokyo", CHFJPY: "Tokyo",
  AUDJPY: "Tokyo", NZDJPY: "Tokyo", GBPJPY: "Tokyo",
  EURJPY: "Tokyo", SGDJPY: "Tokyo",
  // AUD pairs → Sydney
  AUDUSD: "Sydney", AUDNZD: "Sydney", AUDCAD: "Sydney",
  AUDCHF: "Sydney",
  // NZD pairs → Sydney
  NZDUSD: "Sydney", NZDCAD: "Sydney", NZDCHF: "Sydney",
  // CAD pairs → New York
  CADCHF: "New York",
  // Metals / commodities → London (primary fix)
  XAUUSD: "London", XAGUSD: "London", XPTUSD: "London", XPDUSD: "London",
  USOUSD: "New York", UKOUSD: "London", NATGASUSD: "New York",
  // Indices → primary exchange city
  US30: "New York", US500: "New York", NAS100: "New York",
  UK100: "London", GER40: "Frankfurt", FRA40: "Frankfurt",
  JPN225: "Tokyo", AUS200: "Sydney",
  // Crypto → New York (largest trading volume)
  BTCUSD: "New York", ETHUSD: "New York", LTCUSD: "New York",
  XRPUSD: "New York", SOLUSD: "New York", BNBUSD: "New York",
};

function resolveHub(symbol: string): string {
  // Exact match first
  if (SYMBOL_HUB[symbol]) return SYMBOL_HUB[symbol];
  // Suffix heuristic
  if (symbol.endsWith("JPY")) return "Tokyo";
  if (symbol.startsWith("AUD") || symbol.startsWith("NZD")) return "Sydney";
  if (symbol.startsWith("GBP")) return "London";
  if (symbol.startsWith("EUR")) return "Frankfurt";
  return "New York";
}

// ── Helpers ───────────────────────────────────────────────────────────────

function latLonToVec3(lat: number, lon: number, r: number): THREE.Vector3 {
  const phi   = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -r * Math.sin(phi) * Math.cos(theta),
     r * Math.cos(phi),
     r * Math.sin(phi) * Math.sin(theta),
  );
}

function isSessionOpen(hub: MarketHub, utcHour: number): boolean {
  const { openHour: o, closeHour: c } = hub;
  if (o < c) return utcHour >= o && utcHour < c;
  return utcHour >= o || utcHour < c;
}

function arcPoints(a: THREE.Vector3, b: THREE.Vector3, segments = 40): THREE.Vector3[] {
  const pts: THREE.Vector3[] = [];
  const mid = a.clone().add(b).normalize().multiplyScalar(a.length() * 1.3);
  for (let i = 0; i <= segments; i++) {
    const t = i / segments;
    const p = new THREE.Vector3()
      .addScaledVector(a, (1 - t) ** 2)
      .addScaledVector(mid, 2 * t * (1 - t))
      .addScaledVector(b, t ** 2);
    pts.push(p);
  }
  return pts;
}

// ── 3D Components ─────────────────────────────────────────────────────────

function Globe() {
  const meshRef = useRef<THREE.Mesh>(null);
  useFrame((_, dt) => {
    if (meshRef.current) meshRef.current.rotation.y += dt * 0.06;
  });
  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[1, 64, 64]} />
      <meshStandardMaterial color="#0a1628" roughness={0.85} metalness={0.1} />
    </mesh>
  );
}

function GlobeGrid() {
  const lines = useMemo(() => {
    const result: { pts: THREE.Vector3[]; opacity: number }[] = [];
    const R = 1.005;
    for (let lat = -60; lat <= 60; lat += 30) {
      const pts: THREE.Vector3[] = [];
      for (let lon = 0; lon <= 360; lon += 3) pts.push(latLonToVec3(lat, lon - 180, R));
      result.push({ pts, opacity: lat === 0 ? 0.25 : 0.10 });
    }
    for (let lon = 0; lon < 360; lon += 30) {
      const pts: THREE.Vector3[] = [];
      for (let lat = -90; lat <= 90; lat += 3) pts.push(latLonToVec3(lat, lon - 180, R));
      result.push({ pts, opacity: 0.08 });
    }
    return result;
  }, []);
  return (
    <>
      {lines.map((l, i) => (
        <Line key={i} points={l.pts} color="#00d2fd" lineWidth={0.4} transparent opacity={l.opacity} />
      ))}
    </>
  );
}

function HubMarker({ hub, isOpen, hasTrades, onClick }: {
  hub: MarketHub; isOpen: boolean; hasTrades: boolean; onClick: () => void;
}) {
  const pos      = useMemo(() => latLonToVec3(hub.lat, hub.lon, 1.02), [hub]);
  const ringRef  = useRef<THREE.Mesh>(null);
  const tradeRef = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (ringRef.current && isOpen) {
      const s = 1 + 0.35 * Math.sin(t * 2.5);
      ringRef.current.scale.setScalar(s);
      (ringRef.current.material as THREE.MeshBasicMaterial).opacity =
        0.6 * (1 - 0.5 * Math.sin(t * 2.5));
    }
    // Trade marker: brighter pulse when hub has live trades
    if (tradeRef.current && hasTrades) {
      (tradeRef.current.material as THREE.MeshBasicMaterial).opacity =
        0.7 + 0.3 * Math.sin(t * 4);
    }
  });

  return (
    <group position={pos} onClick={onClick}>
      {/* Base dot */}
      <mesh>
        <sphereGeometry args={[0.022, 12, 12]} />
        <meshBasicMaterial color={hub.color} transparent opacity={isOpen ? 1.0 : 0.25} />
      </mesh>
      {/* Open session: pulsing ring */}
      {isOpen && (
        <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[0.032, 0.004, 8, 40]} />
          <meshBasicMaterial color={hub.color} transparent opacity={0.6} />
        </mesh>
      )}
      {/* Live trade indicator: outer glowing ring in white */}
      {hasTrades && (
        <mesh ref={tradeRef} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[0.048, 0.003, 8, 40]} />
          <meshBasicMaterial color="#ffffff" transparent opacity={0.7} />
        </mesh>
      )}
    </group>
  );
}

function TradeArcs({ trades, utcHour }: { trades: LiveTrade[]; utcHour: number }) {
  // Draw arcs from hub → hub for each open trade pair that crosses sessions
  const arcs = useMemo(() => {
    const result: { pts: THREE.Vector3[]; color: string; opacity: number }[] = [];

    // Session overlap arcs (open markets connected)
    const openHubs = HUBS.filter((h) => isSessionOpen(h, utcHour));
    for (let i = 0; i < openHubs.length; i++) {
      for (let j = i + 1; j < openHubs.length; j++) {
        const a = latLonToVec3(openHubs[i].lat, openHubs[i].lon, 1.02);
        const b = latLonToVec3(openHubs[j].lat, openHubs[j].lon, 1.02);
        result.push({ pts: arcPoints(a, b), color: openHubs[i].color, opacity: 0.35 });
      }
    }

    // Live trade arcs: hub → hub for trades with matching base/quote hubs
    trades.forEach((trade) => {
      const primaryHub = HUBS.find((h) => h.name === trade.hub);
      if (!primaryHub) return;
      const base   = trade.symbol.slice(0, 3);
      const quote  = trade.symbol.slice(3);
      const qHub   = SYMBOL_HUB[quote + "USD"] ? resolveHub(quote + "USD") : null;
      const qHubObj = qHub ? HUBS.find((h) => h.name === qHub) : null;
      if (!qHubObj || qHubObj.name === primaryHub.name) return;
      const a = latLonToVec3(primaryHub.lat, primaryHub.lon, 1.03);
      const b = latLonToVec3(qHubObj.lat, qHubObj.lon, 1.03);
      const color = trade.direction === "BUY" ? "#00fd87" : "#ff716c";
      result.push({ pts: arcPoints(a, b, 50), color, opacity: 0.75 });
    });

    return result;
  }, [trades, utcHour]);

  return (
    <>
      {arcs.map((arc, i) => (
        <Line key={i} points={arc.pts} color={arc.color} lineWidth={arc.opacity > 0.5 ? 1.2 : 0.7}
          transparent opacity={arc.opacity} />
      ))}
    </>
  );
}

function Starfield() {
  const pointsRef = useRef<THREE.Points>(null);
  const { positions } = useMemo(() => {
    const n = 1200;
    const pos = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi   = Math.acos(2 * Math.random() - 1);
      const r     = 4 + Math.random() * 4;
      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.cos(phi);
      pos[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);
    }
    return { positions: pos };
  }, []);
  useFrame((_, dt) => { if (pointsRef.current) pointsRef.current.rotation.y += dt * 0.003; });
  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial color="#ffffff" size={0.012} transparent opacity={0.6} />
    </points>
  );
}

function CameraRig() {
  const { camera } = useThree();
  useEffect(() => { camera.position.set(0, 0.5, 2.8); camera.lookAt(0, 0, 0); }, [camera]);
  return null;
}

// ── Info panels ───────────────────────────────────────────────────────────

function SessionPanel({
  utcHour, trades, selected, onSelect,
}: {
  utcHour: number;
  trades: LiveTrade[];
  selected: string | null;
  onSelect: (name: string | null) => void;
}) {
  const tradesByHub = useMemo(() => {
    const map: Record<string, LiveTrade[]> = {};
    trades.forEach((t) => {
      if (!map[t.hub]) map[t.hub] = [];
      map[t.hub].push(t);
    });
    return map;
  }, [trades]);

  const openHubs = HUBS.filter((h) => isSessionOpen(h, utcHour));

  return (
    <div style={{
      background: "rgba(14,14,14,0.7)",
      border: "1px solid #494847",
      borderRadius: 12,
      padding: 20,
      backdropFilter: "blur(12px)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
        <span className="material-symbols-outlined" style={{ color: "#00fd87", fontSize: 18 }}>
          schedule
        </span>
        <span style={{
          fontSize: 11, fontWeight: 700, color: "#adaaaa",
          letterSpacing: "0.15em", fontFamily: "'Fira Code', monospace",
        }}>
          MARKET SESSIONS — {String(utcHour).padStart(2, "0")}:00 UTC
        </span>
        <span style={{
          marginLeft: "auto", fontSize: 10, color: "#adaaaa",
          fontFamily: "'Fira Code', monospace",
        }}>
          {trades.length} LIVE TRADE{trades.length !== 1 ? "S" : ""}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
        {HUBS.map((hub) => {
          const open    = isSessionOpen(hub, utcHour);
          const hubTrades = tradesByHub[hub.name] || [];
          const isSelected = selected === hub.name;
          return (
            <div
              key={hub.name}
              onClick={() => onSelect(isSelected ? null : hub.name)}
              style={{
                padding: "12px 14px",
                borderRadius: 8,
                border: `1px solid ${isSelected ? hub.color + "90" : open ? hub.color + "40" : "#49484740"}`,
                background: isSelected ? hub.color + "18" : open ? hub.color + "0d" : "transparent",
                cursor: "pointer",
                transition: "border-color 0.2s, background 0.2s",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                <span style={{
                  width: 8, height: 8, borderRadius: "50%",
                  background: open ? hub.color : "#494847",
                  boxShadow: open ? `0 0 8px ${hub.color}` : "none",
                  flexShrink: 0,
                }} />
                <span style={{
                  fontSize: 12, fontWeight: 700,
                  color: open ? "#fff" : "#adaaaa",
                  fontFamily: "'Fira Code', monospace",
                  flex: 1,
                }}>
                  {hub.name}
                </span>
                {/* Live trade badge */}
                {hubTrades.length > 0 && (
                  <span style={{
                    fontSize: 9, fontWeight: 700,
                    color: "#fff",
                    background: hub.color,
                    borderRadius: 4,
                    padding: "1px 5px",
                    fontFamily: "'Fira Code', monospace",
                  }}>
                    {hubTrades.length}
                  </span>
                )}
              </div>
              <div style={{
                fontSize: 10, fontWeight: 700, letterSpacing: "0.1em",
                color: open ? hub.color : "#494847", marginBottom: 4,
              }}>
                {open ? "OPEN" : "CLOSED"}
              </div>
              <div style={{ fontSize: 10, color: "#adaaaa" }}>
                {String(hub.openHour).padStart(2, "0")}:00 – {String(hub.closeHour).padStart(2, "0")}:00 UTC
              </div>
            </div>
          );
        })}
      </div>

      {/* Overlap / no-session callout */}
      {openHubs.length >= 2 ? (
        <div style={{
          marginTop: 14, padding: "8px 12px",
          background: "rgba(0,253,135,0.06)", border: "1px solid rgba(0,253,135,0.2)",
          borderRadius: 8, fontSize: 11, color: "#00fd87",
          fontFamily: "'Fira Code', monospace",
        }}>
          ⚡ SESSION OVERLAP: {openHubs.map((h) => h.name).join(" + ")} — highest liquidity window
        </div>
      ) : openHubs.length === 0 ? (
        <div style={{
          marginTop: 14, padding: "8px 12px",
          background: "rgba(73,72,71,0.2)", border: "1px solid #494847",
          borderRadius: 8, fontSize: 11, color: "#adaaaa",
          fontFamily: "'Fira Code', monospace",
        }}>
          — All sessions closed — low liquidity, bot paused
        </div>
      ) : null}
    </div>
  );
}

function HubDetailPanel({
  hub, trades, onClose,
}: {
  hub: MarketHub; trades: LiveTrade[]; onClose: () => void;
}) {
  const totalPnl = trades.reduce((s, t) => s + t.pnl, 0);

  return (
    <div style={{
      background: "rgba(14,14,14,0.7)",
      border: `1px solid ${hub.color}40`,
      borderRadius: 12,
      padding: 20,
      backdropFilter: "blur(12px)",
      minWidth: 0,
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{
            width: 10, height: 10, borderRadius: "50%",
            background: hub.color, boxShadow: `0 0 10px ${hub.color}`,
          }} />
          <span style={{
            fontSize: 14, fontWeight: 700, color: "#fff",
            fontFamily: "'Fira Code', monospace",
          }}>
            {hub.name}
          </span>
        </div>
        <button onClick={onClose} style={{
          background: "none", border: "none", color: "#adaaaa",
          cursor: "pointer", fontSize: 16, lineHeight: 1, padding: 4,
        }}>✕</button>
      </div>

      {trades.length === 0 ? (
        <div style={{
          padding: "16px 12px", textAlign: "center",
          fontSize: 12, color: "#adaaaa",
          fontFamily: "'Fira Code', monospace",
        }}>
          No open trades on {hub.name} pairs
        </div>
      ) : (
        <>
          <div style={{ fontSize: 11, color: "#adaaaa", marginBottom: 8, letterSpacing: "0.1em" }}>
            LIVE TRADES — {trades.length} position{trades.length !== 1 ? "s" : ""}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 240, overflowY: "auto" }}>
            {trades.map((t) => (
              <div key={t.id} style={{
                padding: "8px 10px",
                background: t.direction === "BUY" ? "rgba(0,253,135,0.06)" : "rgba(255,113,108,0.06)",
                border: `1px solid ${t.direction === "BUY" ? "rgba(0,253,135,0.2)" : "rgba(255,113,108,0.2)"}`,
                borderRadius: 6,
                display: "flex",
                alignItems: "center",
                gap: 10,
              }}>
                <span style={{
                  fontSize: 9, fontWeight: 700,
                  color: t.direction === "BUY" ? "#00fd87" : "#ff716c",
                  background: t.direction === "BUY" ? "rgba(0,253,135,0.15)" : "rgba(255,113,108,0.15)",
                  padding: "2px 5px", borderRadius: 3,
                  fontFamily: "'Fira Code', monospace", flexShrink: 0,
                }}>
                  {t.direction}
                </span>
                <span style={{
                  fontSize: 12, fontWeight: 700, color: "#fff",
                  fontFamily: "'Fira Code', monospace", flex: 1,
                }}>
                  {t.symbol}
                </span>
                <span style={{
                  fontSize: 11, fontWeight: 700,
                  color: t.pnl >= 0 ? "#00fd87" : "#ff716c",
                  fontFamily: "'Fira Code', monospace",
                }}>
                  {t.pnl >= 0 ? "+" : ""}{t.pnl.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
          <div style={{
            marginTop: 10, padding: "8px 10px",
            background: totalPnl >= 0 ? "rgba(0,253,135,0.08)" : "rgba(255,113,108,0.08)",
            border: `1px solid ${totalPnl >= 0 ? "rgba(0,253,135,0.2)" : "rgba(255,113,108,0.2)"}`,
            borderRadius: 6,
            display: "flex", justifyContent: "space-between", alignItems: "center",
            fontSize: 11, fontFamily: "'Fira Code', monospace",
          }}>
            <span style={{ color: "#adaaaa" }}>HUB P&L</span>
            <span style={{ fontWeight: 700, color: totalPnl >= 0 ? "#00fd87" : "#ff716c" }}>
              {totalPnl >= 0 ? "+" : ""}{totalPnl.toFixed(2)}
            </span>
          </div>
        </>
      )}
    </div>
  );
}

// ── Main scene ────────────────────────────────────────────────────────────

function Scene({
  utcHour, trades, onHubClick,
}: {
  utcHour: number;
  trades: LiveTrade[];
  onHubClick: (name: string) => void;
}) {
  const tradeHubs = useMemo(() => new Set(trades.map((t) => t.hub)), [trades]);

  return (
    <>
      <CameraRig />
      <ambientLight intensity={0.15} />
      <pointLight position={[4, 3, 3]} intensity={1.2} color="#00d2fd" />
      <pointLight position={[-3, -2, -3]} intensity={0.4} color="#e966ff" />
      <Starfield />
      <Globe />
      <GlobeGrid />
      <TradeArcs trades={trades} utcHour={utcHour} />
      {HUBS.map((hub) => (
        <HubMarker
          key={hub.name}
          hub={hub}
          isOpen={isSessionOpen(hub, utcHour)}
          hasTrades={tradeHubs.has(hub.name)}
          onClick={() => onHubClick(hub.name)}
        />
      ))}
      <OrbitControls
        enableZoom enablePan={false}
        minDistance={1.8} maxDistance={5}
        autoRotate={false} dampingFactor={0.08} enableDamping
      />
    </>
  );
}

// ── Root component ────────────────────────────────────────────────────────

export default function ForexGlobe() {
  const [utcHour, setUtcHour]     = useState(() => new Date().getUTCHours());
  const [trades, setTrades]       = useState<LiveTrade[]>([]);
  const [selected, setSelected]   = useState<string | null>(null);
  const [lastFetch, setLastFetch] = useState<string>("—");
  const [fetchErr, setFetchErr]   = useState(false);

  const fetchTrades = useCallback(async () => {
    try {
      const res = await fetch("/api/trades");
      if (!res.ok) { setFetchErr(true); return; }
      const raw: Array<{ id: string; symbol: string; direction: string;
                         entry_price: number; pnl: number; status: string; open_time: string }> =
        await res.json();
      const mapped: LiveTrade[] = raw.map((t) => ({
        ...t,
        hub: resolveHub(t.symbol),
      }));
      setTrades(mapped);
      setFetchErr(false);
      setLastFetch(new Date().toUTCString().slice(17, 25) + " UTC");
    } catch {
      setFetchErr(true);
    }
  }, []);

  // Live UTC clock + periodic trade refresh (every 30s)
  useEffect(() => {
    fetchTrades();
    const clockId  = setInterval(() => setUtcHour(new Date().getUTCHours()), 60_000);
    const tradeId  = setInterval(fetchTrades, 30_000);
    return () => { clearInterval(clockId); clearInterval(tradeId); };
  }, [fetchTrades]);

  const selectedHub    = selected ? HUBS.find((h) => h.name === selected) ?? null : null;
  const selectedTrades = selected ? trades.filter((t) => t.hub === selected) : [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Canvas */}
      <div style={{
        width: "100%", height: 520, borderRadius: 16, overflow: "hidden",
        border: "1px solid #494847",
        background: "radial-gradient(ellipse at center, #050d1a 0%, #000000 70%)",
        position: "relative",
      }}>
        {/* Legend */}
        <div style={{
          position: "absolute", top: 14, left: 14, zIndex: 10,
          display: "flex", flexDirection: "column", gap: 5,
          fontFamily: "'Fira Code', monospace", fontSize: 10,
          pointerEvents: "none",
        }}>
          {[
            { color: "#ffffff", label: "Active trade on hub" },
            { color: "#00fd87", label: "BUY trade arc" },
            { color: "#ff716c", label: "SELL trade arc" },
          ].map(({ color, label }) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 22, height: 2, background: color, borderRadius: 1 }} />
              <span style={{ color: "#adaaaa" }}>{label}</span>
            </div>
          ))}
        </div>

        {/* Fetch status */}
        <div style={{
          position: "absolute", top: 14, right: 14, zIndex: 10,
          fontSize: 9, color: fetchErr ? "#ff716c" : "#adaaaa",
          fontFamily: "'Fira Code', monospace",
        }}>
          {fetchErr ? "⚠ API UNAVAILABLE" : `UPDATED ${lastFetch}`}
        </div>

        {/* Hint */}
        <div style={{
          position: "absolute", bottom: 14, left: "50%",
          transform: "translateX(-50%)", fontSize: 10, color: "#adaaaa",
          letterSpacing: "0.12em", fontFamily: "'Fira Code', monospace",
          pointerEvents: "none", zIndex: 10, whiteSpace: "nowrap",
        }}>
          DRAG · ZOOM · CLICK MARKER
        </div>

        <Canvas dpr={[1, 2]} gl={{ antialias: true, alpha: true }}
          style={{ width: "100%", height: "100%" }}>
          <Scene utcHour={utcHour} trades={trades} onHubClick={setSelected} />
        </Canvas>
      </div>

      {/* Bottom panels */}
      <div style={{
        display: "grid",
        gridTemplateColumns: selectedHub ? "1fr 300px" : "1fr",
        gap: 16,
        alignItems: "start",
      }}>
        <SessionPanel
          utcHour={utcHour}
          trades={trades}
          selected={selected}
          onSelect={setSelected}
        />
        {selectedHub && (
          <HubDetailPanel
            hub={selectedHub}
            trades={selectedTrades}
            onClose={() => setSelected(null)}
          />
        )}
      </div>
    </div>
  );
}
