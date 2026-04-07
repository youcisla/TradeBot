import React from 'react';

// Example: <AgentBadge agent="council" />
// <AgentBadge agent="risk" active />

export const AgentBadge = ({ agent, active = false }: { agent: string, active?: boolean }) => {
  const agentColors: Record<string, string> = {
    crucix: "bg-[var(--agent-crucix)]",
    market: "bg-[var(--agent-market)]",
    analysis: "bg-[var(--agent-analysis)]",
    strategy: "bg-[var(--agent-strategy)]",
    neural: "bg-[var(--agent-neural)]",
    council: "bg-[var(--agent-council)]",
    risk: "bg-[var(--agent-risk)]",
    execution: "bg-[var(--agent-execution)]",
    manager: "bg-[var(--agent-trade-mgr)]",
    learning: "bg-[var(--agent-learning)]",
    logging: "bg-[var(--agent-logging)]",
    debate: "bg-[var(--agent-debate)]",
    exposure: "bg-[var(--agent-exposure)]",
    memory: "bg-[var(--agent-memory)]",
  };
  
  const bgColors: Record<string, string> = {
    crucix: "bg-[rgba(100,210,255,0.15)] text-[var(--agent-crucix)]",
    market: "bg-[rgba(50,173,230,0.15)] text-[var(--agent-market)]",
    analysis: "bg-[rgba(244,244,245,0.15)] text-[var(--agent-analysis)]",
    strategy: "bg-[rgba(48,209,88,0.15)] text-[var(--agent-strategy)]",
    neural: "bg-[rgba(191,90,242,0.15)] text-[var(--agent-neural)]",
    council: "bg-[rgba(255,159,10,0.15)] text-[var(--agent-council)]",
    risk: "bg-[rgba(255,69,58,0.15)] text-[var(--agent-risk)]",
    execution: "bg-[rgba(240,180,41,0.15)] text-[var(--agent-execution)]",
    manager: "bg-[rgba(100,210,255,0.15)] text-[var(--agent-trade-mgr)]",
    learning: "bg-[rgba(48,209,88,0.15)] text-[var(--agent-learning)]",
    logging: "bg-[rgba(244,244,245,0.10)] text-text-3",
    debate: "bg-[rgba(191,90,242,0.15)] text-[var(--agent-debate)]",
    exposure: "bg-[rgba(255,159,10,0.15)] text-[var(--agent-exposure)]",
    memory: "bg-[rgba(100,210,255,0.15)] text-[var(--agent-memory)]",
  };

  const aKey = agent.toLowerCase().replace('-', '');
  const foundKey = Object.keys(bgColors).find(k => aKey.includes(k)) || 'logging';
  
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-pill uppercase tracking-wider text-[10px] font-mono font-bold border border-border/20 ${bgColors[foundKey]}`}>
      {active && <span className={`w-1.5 h-1.5 rounded-full mr-1.5 animate-pulse ${agentColors[foundKey]}`} />}
      {agent}
    </span>
  );
};

export const LevelBadge = ({ level }: { level: string }) => {
  const l = level.toLowerCase();
  let colors = "bg-bg-3 text-text-2";
  if (l === 'info') colors = "bg-cyan/10 text-cyan";
  if (l === 'warn') colors = "bg-orange/10 text-orange";
  if (l === 'error') colors = "bg-red/10 text-red";

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-sm uppercase text-[10px] font-mono font-bold ${colors}`}>
      {level}
    </span>
  );
};

export const DirectionBadge = ({ direction }: { direction: string }) => {
  const d = direction.toUpperCase();
  const isLong = d === 'LONG' || d === 'BUY';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-sm uppercase text-[10px] font-mono font-bold ${isLong ? 'bg-gold text-bg-2' : 'bg-red text-bg-2'}`}>
      {direction}
    </span>
  );
};

export const StrategyBadge = ({ strategy }: { strategy: string }) => {
  const s = strategy.toLowerCase();
  let colors = "bg-bg-3 text-text-2";
  if (s.includes('ict')) colors = "bg-cyan text-bg-2";
  else if (s.includes('deepseek')) colors = "bg-purple text-bg-2";
  else if (s.includes('ensemble')) colors = "bg-orange text-bg-2";
  else if (s.includes('sma')) colors = "bg-text-3 text-bg-2";

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-pill uppercase tracking-wider text-[10px] font-mono font-bold ${colors}`}>
      {strategy}
    </span>
  );
};
