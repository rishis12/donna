/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Warm earthy tan/brown palette
        surface: {
          50: '#FAF8F5',   // Warm cream
          100: '#F5F0E8',  // Light tan
          200: '#E8DFD3',  // Tan border
          300: '#D4C4B0',  // Darker tan
          400: '#B8A690',  // Muted brown
          500: '#9C8B78',  // Medium brown
          600: '#7D6E5E',  // Brown text
          700: '#5E5247',  // Dark brown
          800: '#443D35',  // Darker brown
          900: '#2D2924',  // Almost black brown
        },
        primary: {
          50: '#F7F3EE',   // Light tan tint
          100: '#EDE5D8',
          200: '#DBC9B0',
          300: '#C9AD88',
          400: '#B89460',  // Main warm tan/caramel
          500: '#A67F4A',
          600: '#8B6A3D',
          700: '#705532',
          800: '#564127',
          900: '#3B2D1C',
        },
        success: {
          400: '#8B9A6F',  // Olive/sage green
          500: '#748259',
        },
        error: {
          400: '#B87060',
          500: '#9C5A4C',
        },
        // Claude Chat Input colors (using CSS variables)
        bg: {
          '0': 'var(--bg-0)',
          '000': 'var(--bg-000)',
          '100': 'var(--bg-100)',
          '200': 'var(--bg-200)',
          '300': 'var(--bg-300)',
        },
        text: {
          100: 'var(--text-100)',
          200: 'var(--text-200)',
          300: 'var(--text-300)',
          400: 'var(--text-400)',
          500: 'var(--text-500)',
        },
        accent: 'var(--accent)',
        'accent-hover': 'var(--accent-hover)',
      },
      fontFamily: {
        sans: ['Georgia', 'Cambria', 'Times New Roman', 'serif'],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.25rem',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
