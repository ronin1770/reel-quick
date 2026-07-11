import {
  DEFAULT_THEME_PREFERENCE,
  THEME_STORAGE_KEY,
} from "@/components/theme";

const themeBootstrapScript = `
  (function () {
    try {
      var storageKey = ${JSON.stringify(THEME_STORAGE_KEY)};
      var defaultPreference = ${JSON.stringify(DEFAULT_THEME_PREFERENCE)};
      var root = document.documentElement;
      var savedPreference = localStorage.getItem(storageKey);
      var preference =
        savedPreference === "light" ||
        savedPreference === "dark" ||
        savedPreference === "system"
          ? savedPreference
          : defaultPreference;
      var resolvedTheme =
        preference === "system" ? "system" : preference;
      var colorScheme = resolvedTheme === "light" ? "light" : "dark";

      root.setAttribute("data-theme", resolvedTheme);
      root.setAttribute("data-theme-preference", preference);
      root.style.colorScheme = colorScheme;
    } catch (error) {
      // Ignore storage or media-query access failures.
    }
  })();
`;

export default function ThemeScript() {
  return <script dangerouslySetInnerHTML={{ __html: themeBootstrapScript }} />;
}
