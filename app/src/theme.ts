// Central design tokens for Plantchi
export const COLORS = {
  bg:        '#0f0f0f',
  card:      '#1a1a1a',
  text:      '#e0e0e0',
  textMuted: '#888888',
  accent:    '#00ff88',
  ok:        '#00ff88',
  warn:      '#ffaa00',
  critical:  '#ff3333',
  border:    '#2a2a2a',
  inputBg:   '#222222',
};

export const SPACING = {
  xs:  4,
  sm:  8,
  md:  16,
  lg:  24,
  xl:  32,
};

export const RADIUS = {
  sm:  8,
  md:  14,
  lg:  20,
  full: 999,
};

export const FONT = {
  regular: { fontWeight: '400' as const },
  bold:    { fontWeight: '700' as const },
  black:   { fontWeight: '900' as const },
};
