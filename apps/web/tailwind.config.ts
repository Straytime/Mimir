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
        surface: "#131313",
        "surface-container-lowest": "#0E0E0E",
        "surface-container-low": "#1B1B1B",
        "surface-container-high": "#2A2A2A",
        primary: "#FFFFFF",
        "on-primary": "#002021",
        "surface-tint": "#00DCE5",
        "primary-container": "#31EAF3",
        secondary: "#C6C6C7",
        tertiary: "#454747",
        "outline-variant": "#474747",
      },
      fontFamily: {
        ui: ["var(--font-ui)", "Space Grotesk", "sans-serif"],
        narrative: ["var(--font-narrative)", "Newsreader", "serif"],
      },
      boxShadow: {
        // Primary button bottom glow (design spec: 2px bottom-glow using surface-tint)
        "glow-sm": "0 2px 0 0 #00DCE5",
        // Stronger glow for hover/active states
        "glow-md": "0 0 12px 0 rgba(0, 220, 229, 0.3)",
        // Input focus left caret (design spec: surface-tint vertical caret on left edge)
        "inset-caret": "inset 2px 0 0 0 #00DCE5",
        // Ghost border simulation (felt not seen)
        "ghost": "inset 0 0 0 1px rgba(71, 71, 71, 0.15)",
      },
      backgroundImage: {
        // CTA gradient: surface-tint to primary-container ("glowing filament")
        "cta-gradient": "linear-gradient(135deg, #00DCE5, #31EAF3)",
        // Subtle radial glow for atmospheric sections
        "radial-glow":
          "radial-gradient(ellipse at 50% 0%, rgba(0, 220, 229, 0.06) 0%, transparent 70%)",
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
          "0%, 100%": { boxShadow: "0 0 4px 0 rgba(0, 220, 229, 0.4)" },
          "50%": { boxShadow: "0 0 12px 2px rgba(0, 220, 229, 0.15)" },
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
            fontFamily: "var(--font-narrative), Newsreader, serif",
          },
        },
      },
    },
  },
  plugins: [typography],
};

export default config;
