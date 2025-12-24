import { defineConfig } from "orval";

export default defineConfig({
  visit: {
    output: {
      mode: "tags-split",
      target: "./generated/visit.ts",
      schemas: "./generated/model",
      client: "react-query",
      mock: true,
      override: {
        mutator: {
          path: "../api/mutator.ts",
          name: "customInstance",
        },
      },
    },
    input: {
      target: "./visit.json",
    },
  },
});
