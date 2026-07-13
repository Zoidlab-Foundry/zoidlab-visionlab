/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#140b11", panel: "#1e131a", panel2: "#261722", line: "#3a2431",
        cy: "#f9a8d4", vi: "#f472b6", ind: "#ec4899", prism: "#f472b6",
        ink: "#f3e8ef", dim: "#b79aac", faint: "#84677a",
        ok: "#22c55e", warn: "#f4b860", bad: "#ef4444",
      },
      boxShadow: {
        glow: "0 0 40px -10px rgba(244,114,182,0.40)",
      },
    },
  },
  plugins: [],
};
