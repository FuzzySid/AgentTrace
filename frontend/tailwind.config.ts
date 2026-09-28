import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {
    colors: { shell: '#141419', page: '#19192c', surface: '#212135', line: '#323248', ink: '#f0f0f5', muted: '#a0a1c0', accent: '#1496FF', fail: '#DA7288', warn: '#E9B86E', pass: '#47AE8F', alt: '#7D6AFA' },
    fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'], mono: ['JetBrains Mono', 'ui-monospace', 'monospace'] },
  } }, plugins: [],
} satisfies Config
