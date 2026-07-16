import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["system-ui", "-apple-system", "Arial", "sans-serif"],
      },
      keyframes: {
        "pop-in": {
          "0%": { transform: "scale(0.85)", opacity: "0" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
        shake: {
          "0%, 100%": { transform: "translateX(0)" },
          "25%": { transform: "translateX(4px)" },
          "75%": { transform: "translateX(-4px)" },
        },
      },
      animation: {
        "pop-in": "pop-in 0.18s ease-out",
        shake: "shake 0.25s ease-in-out",
      },
    },
  },
  plugins: [],
};

export default config;
