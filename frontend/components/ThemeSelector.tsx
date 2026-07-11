"use client";

import { useEffect, useState } from "react";

import {
  DEFAULT_THEME_PREFERENCE,
  isThemePreference,
  resolveThemePreference,
  THEME_STORAGE_KEY,
  type ResolvedTheme,
  type ThemePreference,
} from "@/components/theme";

const getResolvedTheme = (preference: ThemePreference): ResolvedTheme =>
  resolveThemePreference(preference);

const applyThemePreference = (preference: ThemePreference) => {
  const resolvedTheme = getResolvedTheme(preference);
  const root = document.documentElement;
  const colorScheme = resolvedTheme === "light" ? "light" : "dark";

  root.setAttribute("data-theme", resolvedTheme);
  root.setAttribute("data-theme-preference", preference);
  root.style.colorScheme = colorScheme;
  window.localStorage.setItem(THEME_STORAGE_KEY, preference);
};

export default function ThemeSelector() {
  const [mounted, setMounted] = useState(false);
  const [themePreference, setThemePreference] = useState<ThemePreference>(
    DEFAULT_THEME_PREFERENCE
  );

  useEffect(() => {
    const storedPreference = window.localStorage.getItem(THEME_STORAGE_KEY);
    const nextPreference = isThemePreference(storedPreference)
      ? storedPreference
      : DEFAULT_THEME_PREFERENCE;

    setThemePreference(nextPreference);
    applyThemePreference(nextPreference);
    setMounted(true);
  }, []);

  const handleChange = (nextValue: ThemePreference) => {
    setThemePreference(nextValue);
    applyThemePreference(nextValue);
  };

  return (
    <label className="theme-select-wrap">
      <span className="theme-select-label">Appearance</span>
      <select
        aria-label="Select theme"
        className="theme-select"
        disabled={!mounted}
        onChange={(event) =>
          handleChange(event.target.value as ThemePreference)
        }
        value={themePreference}
      >
        <option value="system">System</option>
        <option value="light">Light</option>
        <option value="dark">Dark</option>
      </select>
    </label>
  );
}
