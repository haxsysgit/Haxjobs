// Simple inline SVG icons — no package dependency needed

interface IconProps { size?: number; className?: string; style?: React.CSSProperties; fill?: string }

function icon(path: string, viewBox = '0 0 24 24', defaultFill = 'none') {
  return ({ size = 18, className, style, fill = defaultFill }: IconProps) => (
    <svg width={size} height={size} viewBox={viewBox} fill={fill} stroke="currentColor"
      strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className={className} style={style}>
      <path d={path} />
    </svg>
  )
}

export const Layout = icon('M3 12h18M3 6h18M3 18h18')
export const BarChart = icon('M12 20V10M18 20V4M6 20v-4')
export const Activity = icon('M22 12h-4l-3 9L9 3l-3 9H2')
export const Layers = icon('M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5')
export const User = icon('M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z')
export const Globe = icon('M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z')
export const Home = icon('M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM9 22V12h6v10')
export const Settings = icon('M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z')
export const ChevronLeft = icon('M15 18l-6-6 6-6')
export const ChevronRight = icon('M9 18l6-6-6-6')
export const ChevronDown = icon('M6 9l6 6 6-6')
export const Star = icon('M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z')
export const Search = icon('M21 21l-6-6m2-5a7 7 0 1 1-14 0 7 7 0 0 1 14 0z', '0 0 24 24')
export const Mail = icon('M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zM22 6l-10 7L2 6')
export const Send = icon('M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z')
export const FileText = icon('M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8')
export const ExternalLink = icon('M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3')
export const CheckCircle = icon('M22 11.08V12a10 10 0 1 1-5.93-9.14M22 4L12 14.01l-3-3')
export const AlertCircle = icon('M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 8v4M12 16h.01')
export const Clock = icon('M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2')
export const TrendingUp = icon('M23 6l-9.5 9.5-5-5L1 18M17 6h6v6')
export const Zap = icon('M13 2L3 14h9l-1 8 10-12h-9l1-8z')
export const Menu = icon('M3 12h18M3 6h18M3 18h18')
export const X = icon('M18 6L6 18M6 6l12 12')

// Sidebar nav items
export const icons = {
  home: Home,
  pipeline: Layers,
  activity: Activity,
  profile: User,
  discovery: Globe,
  settings: Settings,
  outreach: Send,
}
