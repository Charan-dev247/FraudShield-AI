/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ['"Schibsted Grotesk"', "system-ui", "sans-serif"] },
      colors: {
        ink: { DEFAULT: "#0E1B26", soft: "#2A3A47", muted: "#5B6B78" },
        fog: { DEFAULT: "#E9EEF0", line: "#D3DCE0" },
        tide: { DEFAULT: "#0B5D6B", dark: "#084854", wash: "#DCEBED" },
        alarm: { DEFAULT: "#D9422B", wash: "#FBE4DF" },
        amber: { DEFAULT: "#B7790A", wash: "#F8EBCB" },
        safe: { DEFAULT: "#2E7D5B", wash: "#DDEFE6" },
      },
    },
  },
  plugins: [],
};
