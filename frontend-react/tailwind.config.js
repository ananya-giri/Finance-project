/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0f172a',
        sidebar: '#111827',
        card: '#1e293b',
        border: '#334155',
        'accent-indigo': '#6366f1',
        'accent-cyan': '#06b6d4',
        'text-primary': '#f8fafc',
        'text-muted': '#94a3b8',
      },
    },
  },
  plugins: [],
}
