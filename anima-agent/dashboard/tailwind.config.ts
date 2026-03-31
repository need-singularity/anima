import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          0: "#0a0a0f",
          1: "#12121a",
          2: "#1a1a26",
          3: "#242434",
        },
        accent: {
          phi: "#6ee7b7",
          tension: "#f97316",
          pnl: {
            pos: "#22c55e",
            neg: "#ef4444",
          },
          regime: {
            bull: "#22c55e",
            bear: "#ef4444",
            range: "#eab308",
            unknown: "#6b7280",
          },
        },
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
