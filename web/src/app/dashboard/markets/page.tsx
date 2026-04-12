export default function MarketIntelPage() {
  return (
    <div style={styles.wrapper}>
      <span style={styles.icon}>◎</span>
      <p style={styles.title}>Market Intelligence</p>
      <p style={styles.sub}>Macro intelligence view coming in a future update.</p>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: "var(--space-3)",
    minHeight: 300,
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    padding: "var(--space-6)",
    textAlign: "center",
  },
  icon: {
    fontSize: 40,
    color: "var(--text-3)",
    opacity: 0.4,
  },
  title: {
    fontFamily: "var(--font-ui)",
    fontSize: 16,
    fontWeight: 700,
    color: "var(--text-1)",
    margin: 0,
  },
  sub: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    color: "var(--text-3)",
    margin: 0,
  },
};
