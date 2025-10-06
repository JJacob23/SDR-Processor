/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#121212",
        active: "#c2c2c2ff",
        inactive: "#444444",
      },
    },
  },
  plugins: [],
}
