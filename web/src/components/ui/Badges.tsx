import React from 'react';

// Example: <AgentBadge agent="council" />
// <AgentBadge agent="risk" active />

const AGENT_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  crucix:    { bg: 'rgba(100,210,255,0.15)', text: '#64d2ff', border: 'rgba(100,210,255,0.30)' },
  market:    { bg: 'rgba(50,173,230,0.15)', text: '#32ade6', border: 'rgba(50,173,230,0.30)' },
  analysis:  { bg: 'rgba(244,244,245,0.10)', text: '#b8b8bc', border: 'rgba(244,244,245,0.20)' },
  strategy:  { bg: 'rgba(48,209,88,0.15)',  text: '#30d158', border: 'rgba(48,209,88,0.30)' },
  neural:    { bg: 'rgba(191,90,242,0.15)', text: '#bf5af2', border: 'rgba(191,90,242,0.30)' },
  council:   { bg: 'rgba(255,159,10,0.15)', text: '#ff9f0a', border: 'rgba(255,159,10,0.30)' },
  risk:      { bg: 'rgba(255,69,58,0.15)',  text: '#ff453a', border: 'rgba(255,69,58,0.30)' },
  execution: { bg: 'rgba(240,180,41,0.15)', text: '#f0b429', border: 'rgba(240,180,41,0.30)' },
  manager:   { bg: 'rgba(100,210,255,0.15)', text: '#64d2ff', border: 'rgba(100,210,255,0.30)' },
  learning:  { bg: 'rgba(48,209,88,0.15)',  text: '#30d158', border: 'rgba(48,209,88,0.30)' },
  logging:   { bg: 'rgba(244,244,245,0.08)', text: '#adaaaa', border: 'rgba(244,244,245,0.15)' },
  debate:    { bg: 'rgba(191,90,242,0.15)', text: '#bf5af2', border: 'rgba(191,90,242,0.30)' },
  exposure:  { bg: 'rgba(255,159,10,0.15)', text: '#ff9f0a', border: 'rgba(255,159,10,0.30)' },
  memory:    { bg: 'rgba(100,210,255,0.15)', text: '#64d2ff', border: 'rgba(100,210,255,0.30)' },
};

const LEVEL_COLORS: Record<string, { bg: string; text: string }> = {
  info:  { bg: 'rgba(0,229,255,0.12)',  text: '#00e5ff' },
  warn:  { bg: 'rgba(255,159,10,0.12)', text: '#ff9f0a' },
  error: { bg: 'rgba(255,69,58,0.12)',  text: '#ff453a' },
};

export const AgentBadge = ({ agent, active = false }: { agent: string; active?: boolean }) => {
  const key = agent.toLowerCase().replace('-', '');
  const found = Object.keys(AGENT_COLORS).find(k => key.includes(k)) || 'logging';
  const c = AGENT_COLORS[found];

  return (
    <span
      style={{
        display:        'inline-flex',
        alignItems:     'center',
        padding:        '2px 8px',
        borderRadius:   9999,
        fontSize:       10,
        fontFamily:     'var(--font-mono)',
        fontWeight:     700,
        textTransform:  'uppercase',
        letterSpacing:  '0.08em',
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
            borderRadius: '50%',
            marginRight:  6,
            backgroundColor: c.text,
            animation:    'pulse 1.5s ease-in-out infinite',
          }}
        />
      )}
      {agent}
    </span>
  );
};

export const LevelBadge = ({ level }: { level: string }) => {
  const l = level.toLowerCase();
  const c = LEVEL_COLORS[l] || { bg: 'rgba(244,244,245,0.10)', text: '#adaaaa' };

  return (
    <span
      style={{
        display:        'inline-flex',
        alignItems:     'center',
        padding:        '2px 8px',
        borderRadius:   4,
        fontSize:       10,
        fontFamily:     'var(--font-mono)',
        fontWeight:     700,
        textTransform:  'uppercase',
        backgroundColor: c.bg,
        color:          c.text,
      }}
    >
      {level}
    </span>
  );
};

export const DirectionBadge = ({ direction }: { direction: string }) => {
  const d = direction.toUpperCase();
  const isLong = d === 'LONG' || d === 'BUY';

  return (
    <span
      style={{
        display:        'inline-flex',
        alignItems:     'center',
        padding:        '2px 8px',
        borderRadius:   4,
        fontSize:       10,
        fontFamily:     'var(--font-mono)',
        fontWeight:     700,
        textTransform:  'uppercase',
        backgroundColor: isLong ? '#f0b429' : '#ff453a',
        color:          '#0e0e0e',
      }}
    >
      {direction}
    </span>
  );
};

export const StrategyBadge = ({ strategy }: { strategy: string }) => {
  const s = strategy.toLowerCase();
  let bg = 'rgba(244,244,245,0.10)';
  let text = '#adaaaa';

  if (s.includes('ict'))      { bg = 'rgba(0,229,255,0.20)';  text = '#00e5ff'; }
  else if (s.includes('deepseek')) { bg = 'rgba(191,90,242,0.20)'; text = '#bf5af2'; }
  else if (s.includes('ensemble')) { bg = 'rgba(255,159,10,0.20)'; text = '#ff9f0a'; }
  else if (s.includes('sma'))     { bg = 'rgba(173,170,170,0.20)'; text = '#adaaaa'; }

  return (
    <span
      style={{
        display:        'inline-flex',
        alignItems:     'center',
        padding:        '2px 8px',
        borderRadius:   9999,
        fontSize:       10,
        fontFamily:     'var(--font-mono)',
        fontWeight:     700,
        textTransform:  'uppercase',
        letterSpacing:  '0.08em',
        backgroundColor: bg,
        color:          text,
      }}
    >
      {strategy}
    </span>
  );
};
