export const THEME_STORAGE_KEY = "reel-quick-theme-preference";

export type ThemePreference = "system" | "light" | "dark";
export type ResolvedTheme = "system" | "light" | "dark";

export const DEFAULT_THEME_PREFERENCE: ThemePreference = "system";

export const isThemePreference = (
  value: string | null | undefined
): value is ThemePreference =>
  value === "system" || value === "light" || value === "dark";

export const resolveThemePreference = (
  preference: ThemePreference,
): ResolvedTheme => {
  if (preference === "system") {
    return "system";
  }

  return preference;
};
