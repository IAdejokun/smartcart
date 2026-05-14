/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Distinctive brand palette — blue/teal duotone with warm accent
        // Avoids the default "Tailwind blue button" aesthetic
        brand: {
          50: "#f0fdfa",
          100: "#ccfbf1",
          500: "#0d9488",
          600: "#0f766e",
          700: "#115e59",
          900: "#134e4a",
        },
        accent: {
          500: "#f59e0b",
          600: "#d97706",
        },
        landing: {
    bg: "#0a1015",        // deep navy-black, slightly cooler than portfolio
    surface: "#0f1820",   // elevated surfaces
    subtle: "#1a2530",    // borders, hover states
    ink: "#f0f5f3",       // primary text — slight cool cream
    inkMuted: "#94a3a8",  // secondary text
    inkSubtle: "#5a6a72", // tertiary text
  },
      },
      fontFamily: {
        serif: ['"Fraunces"', "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
