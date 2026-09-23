import { defineConfig } from "vitest/config";
import type { IndexHtmlTransformContext } from "vite";
import react from "@vitejs/plugin-react";

const RUNTIME_CONFIGURABLE_ENV_VARS = [
  "VSETH_ORG_CONFIG",
  "VISIT_BACKEND_WEB_URL",
  "VIS_WEBSITE_URL",
];

const envsubstFormatIsRequested = () =>
  process.env.REPLACE_ENV_FORMAT_ENVSUBST === "true";

const withEnvsubstPlaceholders = (html: string) =>
  RUNTIME_CONFIGURABLE_ENV_VARS.reduce(
    (previous, current) =>
      previous.replaceAll(`%VITE_${current}%`, `\${${current}}`),
    html,
  );

const nginxEnvsubstVarsPlugin = () => ({
  name: "vite-plugin-nginx-envsubst-vars",
  transformIndexHtml: {
    order: "pre" as const,
    handler: (html: string, { server }: IndexHtmlTransformContext) => {
      const isViteDevServer = Boolean(server);
      if (isViteDevServer || !envsubstFormatIsRequested()) return;
      return withEnvsubstPlaceholders(html);
    },
  },
});

export default defineConfig({
  server: {
    port: 3000,
    strictPort: true,
  },
  test: {
    isolate: false,
    environment: "jsdom",
    environmentOptions: {
      jsdom: {
        url: "http://localhost:3000/",
      },
    },
    setupFiles: ["./src/test/setupTests.ts"],
    clearMocks: true,
    restoreMocks: true,
    css: false,
  },
  plugins: [react(), nginxEnvsubstVarsPlugin()],
});
