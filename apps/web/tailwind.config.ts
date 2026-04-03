import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
    "./tests/**/*.{ts,tsx}",
  ],
  theme: {
    borderRadius: {
      DEFAULT: "0px",
      none: "0px",
      full: "9999px",
    },
    extend: {
      colors: {
        surface: "#000000",
        "surface-container-lowest": "#000000",
        "surface-container-low": "#1a1919",
        "surface-container": "#1a1919",
        "surface-container-high": "#2c2c2c",
        "surface-bright": "#2c2c2c",
        primary: "#ffad3a",
        "on-primary": "#000000",
        "on-primary-fixed": "#000000",
        "primary-container": "#f59e0a",
        secondary: "#C6C6C7",
        tertiary: "#454747",
        outline: "#777575",
        "outline-variant": "#494847",
        "on-surface": "#C6C6C7",
        "surface-variant": "#2c2c2c",
      },
      fontFamily: {
        ui: ["var(--font-ui)", "Space Grotesk", "sans-serif"],
        narrative: ["var(--font-narrative)", "Inter", "sans-serif"],
      },
      boxShadow: {
        // Primary button bottom glow (design spec: 2px bottom-glow using primary amber)
        "glow-sm": "0 2px 0 0 #ffad3a",
        // Stronger glow for hover/active states
        "glow-md": "0 0 12px 0 rgba(255, 173, 58, 0.3)",
        // Input focus left caret (design spec: primary amber vertical caret on left edge)
        "inset-caret": "inset 2px 0 0 0 #ffad3a",
        // Ghost border simulation (felt not seen)
        "ghost": "inset 0 0 0 1px rgba(73, 72, 71, 0.15)",
        // Focus outer glow (DESIGN.md: primary at 20% opacity)
        "focus-glow": "0 0 0 2px rgba(255, 173, 58, 0.2)",
      },
      backgroundImage: {
        // CTA gradient: primary to primary-container ("glowing filament")
        "cta-gradient": "linear-gradient(135deg, #ffad3a, #f59e0a)",
        // Subtle radial glow for atmospheric sections
        "radial-glow":
          "radial-gradient(ellipse at 50% 0%, rgba(255, 173, 58, 0.06) 0%, transparent 70%)",
      },
      spacing: {
        "sp-2": "0.7rem",
        "sp-6": "2rem",
        "sp-8": "2.75rem",
        "sp-10": "3.5rem",
      },
      keyframes: {
        "pulse-slow": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
        "glow-pulse": {
          "0%, 100%": { boxShadow: "0 0 4px 0 rgba(255, 173, 58, 0.4)" },
          "50%": { boxShadow: "0 0 12px 2px rgba(255, 173, 58, 0.15)" },
        },
      },
      animation: {
        "pulse-slow": "pulse-slow 2s ease-in-out infinite",
        "pulse-fast": "pulse-slow 0.8s ease-in-out infinite",
        "fade-in-up": "fade-in-up 0.5s ease-out both",
        scan: "scan 2s linear infinite",
        "glow-pulse": "glow-pulse 3s ease-in-out infinite",
      },
      typography: {
        invert: {
          css: {
            fontFamily: "var(--font-narrative), Inter, sans-serif",
          },
        },
      },
    },
  },
  plugins: [typography],
};

export default config;
