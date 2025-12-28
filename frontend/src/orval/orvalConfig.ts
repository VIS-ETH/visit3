import { defineConfig } from "orval";

export default defineConfig({
  visit: {
    output: {
      mode: "tags-split",
      target: "./generated/",
      client: "react-query",
      mock: false,
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
