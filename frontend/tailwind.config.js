/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#f4f7fb",
        ink: "#132238",
        accent: {
          50: "#eef4ff",
          100: "#d8e6ff",
          500: "#5f79ff",
          600: "#4f63e6",
          700: "#4050b8",
        },
      },
      boxShadow: {
        panel: "0 16px 40px rgba(15, 23, 42, 0.08)",
      },
      backgroundImage: {
        "brand-grid":
          "radial-gradient(circle at 1px 1px, rgba(95,121,255,0.10) 1px, transparent 0)",
      },
    },
  },
  plugins: [],
};
