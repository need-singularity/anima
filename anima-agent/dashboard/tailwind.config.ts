import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          0: "#08080c",
          1: "#0e0e14",
          2: "#15151e",
          3: "#1e1e2c",
          4: "#2a2a3a",
        },
        glow: {
          phi: "#4ade80",
          tension: "#fb923c",
          danger: "#f87171",
        },
        accent: {
          cyan: "#22d3ee",
          amber: "#fbbf24",
        },
      },
      fontFamily: {
        sans: ["'DM Sans'", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ["'Azeret Mono'", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
