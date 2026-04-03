import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["-apple-system", "BlinkMacSystemFont", "'SF Pro Display'", "'SF Pro Text'", "system-ui", "sans-serif"],
        mono: ["'SF Mono'", "Menlo", "Monaco", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
