/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#000000",
        active: "#00ff00",
        inactive: "#444444",
      },
    },
  },
  plugins: [],
}
