// The few icons the page uses, drawn as inline SVG (one stroke weight).
export default function Icon({ name, size = 16 }) {
  const p = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true }
  if (name === 'chev') return <svg {...p}><path d="M6 9l6 6 6-6" /></svg>
  if (name === 'edit') return <svg {...p}><path d="M4 20h4L19 9l-4-4L4 16v4z" /></svg>
  return <svg {...p}><circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16h.01" /></svg>
}
