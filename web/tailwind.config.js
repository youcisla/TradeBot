/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        matrix: "#00ff41",
        "matrix-dim": "#00cc33",
        terminal: "#0a0a0a",
        "terminal-surface": "#111111",
        "terminal-border": "#1a1a1a",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
};
