import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        poke: {
          red: "#CC0000",
          yellow: "#FFCB05",
          dark: "#0D0D0D",
          card: "#1A1A1A",
          border: "#2A2A2A",
        },
      },
    },
  },
  plugins: [],
};

export default config;
