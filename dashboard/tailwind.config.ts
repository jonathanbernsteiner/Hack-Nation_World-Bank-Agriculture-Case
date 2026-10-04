import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["DM Sans", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      colors: {
        surface: "#F9FAFB",
        accent: "#3B82F6",
        ai: "#8B5CF6",
        navy: "#0B1628",
        ink: "#0F172A",
        muted: "#64748B",
        faint: "#94A3B8",
        line: "#E2E8F0",
        divider: "#F1F5F9",
      },
    },
  },
  plugins: [typography],
};

export default config;
