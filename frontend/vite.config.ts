import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/

// List of all environment variables that are required to be configurable at runtime
const ENV_VARS_FOR_ENVSUBST = [
  "VSETH_ORG_CONFIG",
  "VISIT_BACKEND_WEB_URL",
];

export default defineConfig({
  server: {
    port: 3000, 
    strictPort: true,
  },
  plugins: [
    react(),

    /**
     * Explicit server magic:
     *
     * We require dynamic theming based on runtime environment variables.
     * These environment variables can be set at dev time in .env.development.
     *
     * During runtime in production, they should be replaced at the start of the container.
     * To host these generated files, we use nginx.
     * The official default container for nginx allows envsubst to template the files at startup before hosting them.
     * This inline Vite plugin will transform all the listed env variables explicitly at build time to an envsubst-friendly format.
     * This simply means, for known env vars of the form $ENV_VAR_EXAMPLE%, transform to ${ENV_VAR_EXAMPLE}
     *
     * NOTE: env vars must be prefixed by VITE_ in the index.html file, as otherwise Vite will not replace the vars at build time (for dev mode)
     */
    {
      name: "vite-plugin-nginx-envsubst-vars",
      transformIndexHtml: {
        // pre: replace before Vite even looks at index.html -> no warnings due to %ENV_VAR_EXAMPLE% missing (potential typo warning).
        order: "pre",
        handler: (html, { server }) => {
          // If using the vite server and not bundler: dev mode - do not change anything to use .env.development variables
          if (!!server) return;

          // Plugin only does something if enabled...
          if (process.env.REPLACE_ENV_FORMAT_ENVSUBST !== "true") return;

          // Go through all env vars, replace the format. These will then be set at nginx startup
          return ENV_VARS_FOR_ENVSUBST.reduce((previous, current, _) => {
            return previous.replaceAll(`%VITE_${current}%`, `\$\{${current}\}`);
          }, html);
        },
      },
    },
  ],
});
