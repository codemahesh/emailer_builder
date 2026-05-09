/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Neutral palette
        neutral: {
          0:   '#FFFFFF',
          50:  '#F8F9FB',
          100: '#EEF1F5',
          200: '#DDE3EB',
          400: '#8A94A6',
          600: '#4A5567',
          800: '#1F2937',
          900: '#0F1623',
        },
        // Brand
        brand: {
          primary:      '#2E5BFF',
          'primary-hover': '#1E47D9',
          'primary-soft':  '#E8EEFF',
        },
        // Semantic
        success: {
          600: '#0F8A4A',
          50:  '#E7F6EC',
        },
        warn: {
          600: '#C2761B',
          50:  '#FDF3E2',
        },
        danger: {
          600: '#C8281F',
          50:  '#FCE8E6',
        },
        info: {
          600: '#1B6AB0',
          50:  '#E5F1FB',
        },
        // Provenance
        prov: {
          ai:     '#7B3FE4',
          manual: '#0F8A4A',
          scrape: '#4A5567',
          locked: '#1F2937',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          '"Helvetica Neue"',
          'Arial',
          '"Noto Sans"',
          'sans-serif',
        ],
      },
      spacing: {
        1: '4px',
        2: '8px',
        3: '12px',
        4: '16px',
        6: '24px',
        8: '32px',
        12: '48px',
      },
      borderRadius: {
        sm:   '4px',
        md:   '8px',
        lg:   '12px',
        full: '999px',
      },
      boxShadow: {
        'elev-flat':   '0 1px 2px 0 rgba(15,22,35,0.06)',
        'elev-raised': '0 4px 12px 0 rgba(15,22,35,0.10), 0 1px 3px 0 rgba(15,22,35,0.06)',
        'elev-overlay':'0 8px 24px 0 rgba(15,22,35,0.14), 0 2px 6px 0 rgba(15,22,35,0.08)',
        'elev-modal':  '0 20px 60px 0 rgba(15,22,35,0.20), 0 4px 16px 0 rgba(15,22,35,0.10)',
      },
      fontSize: {
        'display':       ['28px', { lineHeight: '36px', fontWeight: '700' }],
        'heading-1':     ['24px', { lineHeight: '32px', fontWeight: '600' }],
        'heading-2':     ['20px', { lineHeight: '28px', fontWeight: '600' }],
        'heading-3':     ['16px', { lineHeight: '24px', fontWeight: '600' }],
        'body':          ['14px', { lineHeight: '20px', fontWeight: '400' }],
        'body-strong':   ['14px', { lineHeight: '20px', fontWeight: '600' }],
        'small':         ['12px', { lineHeight: '16px', fontWeight: '400' }],
        'small-strong':  ['12px', { lineHeight: '16px', fontWeight: '600' }],
        'caption':       ['11px', { lineHeight: '14px', fontWeight: '400' }],
      },
      width: {
        'login-card':  '400px',
        'modal-sm':    '480px',
        'left-rail':   '380px',
      },
      height: {
        'topbar':       '56px',
        'dashboard-header': '80px',
        'card-thumb':   '160px',
      },
      minHeight: {
        'campaign-card': '240px',
      },
      animation: {
        shimmer: 'shimmer 1.5s infinite',
      },
      keyframes: {
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
    },
  },
  plugins: [],
}
