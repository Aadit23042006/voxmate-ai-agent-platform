// VoxMate design system — "Futuristic Neon + Premium Minimal"
// Single source of truth for color, spacing, radius, and type so every
// screen reads as one consistent, premium AI-OS surface instead of a
// generic chatbot UI.

export const colors = {
  // Backgrounds
  bg: "#050617",
  bgAlt: "#07091A",
  bgSecondary: "#0B1024",
  surface: "#10162D",
  surfaceElevated: "#151B36",

  // Accents
  purple: "#7C4DFF",
  purpleSoft: "#9B6CFF",
  blue: "#2979FF",
  cyan: "#00D9FF",

  // Text
  textPrimary: "#FFFFFF",
  textSecondary: "#A9B1C6",
  textMuted: "#68718A",

  // Status
  success: "#35D07F",
  error: "#FF557A",

  // Glass
  glassBorder: "rgba(255,255,255,0.10)",
  glassBorderStrong: "rgba(255,255,255,0.16)",
  glassFill: "rgba(255,255,255,0.05)",
} as const;

// Electric Purple → Neon Blue → Cyan — the one recurring brand gradient.
export const gradients = {
  brand: [colors.purple, colors.blue, colors.cyan] as const,
  brandDuo: [colors.purple, colors.cyan] as const,
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
};

export const radius = {
  sm: 10,
  md: 16,
  lg: 20,
  xl: 28,
  pill: 999,
};

export const type = {
  greeting: { fontSize: 26, fontWeight: "600" as const, letterSpacing: 0.1 },
  screenTitle: { fontSize: 20, fontWeight: "700" as const },
  cardTitle: { fontSize: 15, fontWeight: "600" as const },
  body: { fontSize: 14, fontWeight: "400" as const },
  secondary: { fontSize: 12.5, fontWeight: "500" as const },
  button: { fontSize: 14.5, fontWeight: "600" as const },
};

export function timeGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good Morning";
  if (h < 17) return "Good Afternoon";
  return "Good Evening";
}
