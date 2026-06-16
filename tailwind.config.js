/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        bench: '#0D1117',
        parchment: '#F5F0E8',
        gavel: '#C9A84C',
        verdict: '#1A6B3C',
        dispute: '#8B2020',
        neutral: '#4A5568',
        chamber: '#161B22',
        border: '#30363D',
        ledger: '#21262D',
      },
    },
  },
  plugins: [],
}
