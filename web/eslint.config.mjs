import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

const nextConfig = nextVitals.map((config) => {
  if (config.name !== "next") return config;
  return {
    ...config,
    rules: {
      ...config.rules,
      // Existing auth/data-loading effects intentionally synchronize async external state.
      // Keep the React 19 rule visible during release polish without turning CP4 into
      // a broad behavior refactor across auth, scan recovery, and analysis flows.
      "react-hooks/set-state-in-effect": "warn",
    },
  };
});

const eslintConfig = defineConfig([
  ...nextConfig,
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);

export default eslintConfig;
