import type { Config } from "tailwindcss";

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
      spacing: {
        "sp-2": "0.7rem",
        "sp-6": "2rem",
        "sp-8": "2.75rem",
        "sp-10": "3.5rem",
      },
    },
  },
  plugins: [],
};

export default config;
