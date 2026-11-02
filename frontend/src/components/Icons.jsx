// Every icon the page uses, drawn once. 1.5-1.8 px strokes, currentColor, hidden from screen readers (the button names them).
const base = { fill: 'none', 'aria-hidden': true }

export const Logo = () => (
  <svg width="22" height="26" viewBox="0 0 22 26" {...base}>
    <path d="M2.5 1.5h12l5 5v18h-17z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    <path d="M6.5 1.5v23" stroke="var(--pen)" strokeWidth="1.6" />
    <path d="M9.5 10h6M9.5 14h6M9.5 18h4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
  </svg>
)
// the copy glyph's two squares put its weight low and right, so it is nudged 0.5 px inside its 44 px box
export const Copy = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" style={{ transform: 'translate(0.5px, 0.5px)' }} {...base}>
    <rect x="5.75" y="5.75" width="9.5" height="9.5" rx="2" stroke="currentColor" strokeWidth="1.5" />
    <path d="M12.25 3.5v-.25a1 1 0 0 0-1-1h-7a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h.25" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
)
export const Check = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" {...base}>
    <path d="M3.75 9.5l3.25 3.25 7.25-7.5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)
// sits 1 px low so its circle lines up with the label's x-height, not its cap height
export const Info = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" style={{ marginTop: 1 }} {...base}>
    <circle cx="9" cy="9" r="7.25" stroke="currentColor" strokeWidth="1.5" />
    <path d="M9 8v4.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    <circle cx="9" cy="5.4" r="0.95" fill="currentColor" />
  </svg>
)
export const Alert = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" {...base}>
    <circle cx="10" cy="10" r="8.25" stroke="currentColor" strokeWidth="1.6" />
    <path d="M10 5.75v5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    <circle cx="10" cy="13.9" r="1.05" fill="currentColor" />
  </svg>
)
export const ChevronRight = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" style={{ transform: 'translateX(1px)' }} {...base}>
    <path d="M6 3.5L10.5 8 6 12.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)
export const ChevronDown = () => (
  <svg width="10" height="10" viewBox="0 0 10 10" {...base}>
    <path d="M2 3.5L5 6.5 8 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)
export const Upload = () => (
  <svg width="22" height="22" viewBox="0 0 22 22" {...base}>
    <path d="M11 14V3.5M6.5 8L11 3.5 15.5 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M3.5 13.5v3a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
  </svg>
)
export const Close = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" {...base}>
    <path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
  </svg>
)
export const Menu = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" {...base}>
    <path d="M3.5 6h13M3.5 10h13M3.5 14h13" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
  </svg>
)
export const Spinner = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" {...base} className="gw-spin">
    <circle cx="8" cy="8" r="6.25" strokeWidth="1.75" style={{ stroke: 'var(--spin-track, oklch(1 0 0 / 0.35))' }} />   {/* the faint ring: pale on the blue button, set by --spin-track elsewhere */}
    <path d="M14.25 8A6.25 6.25 0 0 0 8 1.75" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
  </svg>
)
