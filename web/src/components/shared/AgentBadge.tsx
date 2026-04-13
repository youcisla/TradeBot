"use client";

interface AgentBadgeProps {
  agent: string;
  /** Show a pulsing live dot */
  active?: boolean;
}

/** Coloured chip per agent name. Maps to agent CSS vars. */
export function AgentBadge({ agent, active = false }: AgentBadgeProps) {
  const key = agent.toLowerCase().replace(/-/g, "");

  const COLORS: Record<string, { bg: string; text: string; border: string }> = {
    crucix:    { bg: "rgba(100,210,255,0.15)", text: "#64d2ff", border: "rgba(100,210,255,0.30)" },
    market:    { bg: "rgba(50,173,230,0.15)",  text: "#32ade6",  border: "rgba(50,173,230,0.30)"  },
    analysis:  { bg: "rgba(244,244,245,0.10)", text: "#b8b8bc", border: "rgba(244,244,245,0.20)" },
    strategy:  { bg: "rgba(48,209,88,0.15)",  text: "#30d158",  border: "rgba(48,209,88,0.30)"  },
    neural:    { bg: "rgba(191,90,242,0.15)", text: "#bf5af2", border: "rgba(191,90,242,0.30)" },
    council:   { bg: "rgba(255,159,10,0.15)", text: "#ff9f0a", border: "rgba(255,159,10,0.30)" },
    risk:      { bg: "rgba(255,69,58,0.15)",  text: "#ff453a", border: "rgba(255,69,58,0.30)"  },
    execution: { bg: "rgba(240,180,41,0.15)", text: "#f0b429", border: "rgba(240,180,41,0.30)" },
    manager:   { bg: "rgba(100,210,255,0.15)", text: "#64d2ff", border: "rgba(100,210,255,0.30)" },
    learning:  { bg: "rgba(48,209,88,0.15)",  text: "#30d158", border: "rgba(48,209,88,0.30)"  },
    logging:   { bg: "rgba(244,244,245,0.08)", text: "#adaaaa", border: "rgba(244,244,245,0.15)" },
    debate:    { bg: "rgba(191,90,242,0.15)", text: "#bf5af2", border: "rgba(191,90,242,0.30)" },
    exposure:  { bg: "rgba(255,159,10,0.15)", text: "#ff9f0a", border: "rgba(255,159,10,0.30)" },
    memory:    { bg: "rgba(100,210,255,0.15)", text: "#64d2ff", border: "rgba(100,210,255,0.30)" },
  };

  const c = Object.keys(COLORS).find((k) => key.includes(k)) ? COLORS[key] : COLORS.logging;

  return (
    <span
      style={{
        display:        "inline-flex",
        alignItems:     "center",
        gap:            active ? 5 : 0,
        padding:        "2px 7px",
        borderRadius:   9999,
        fontSize:       10,
        fontFamily:     "var(--font-mono)",
        fontWeight:     700,
        textTransform:  "uppercase",
        letterSpacing: "0.07em",
        backgroundColor: c.bg,
        color:          c.text,
        border:         `1px solid ${c.border}`,
      }}
    >
      {active && (
        <span
          style={{
            width:        6,
            height:       6,
            borderRadius: "50%",
            background:   c.text,
            animation:    "pulse-dot 1.5s ease-in-out infinite",
          }}
        />
      )}
      {agent}
    </span>
  );
}
