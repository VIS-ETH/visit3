import { describe, expect, it } from "vitest";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";

const nginxDir = path.join(process.cwd(), "nginx");
const script = "18-visit-runtime-env.envsh";
const template = readFileSync(
  path.join(nginxDir, "default.conf.template"),
  "utf8",
);
const RUNTIME_VARIABLES = ["VISIT_STORAGE_PUBLIC_URL", "VISIT_BACKEND_WEB_URL"];

const sourceScript = (env: Record<string, string>) => {
  const inherited = Object.fromEntries(
    Object.entries(process.env).filter(
      ([name]) => !RUNTIME_VARIABLES.includes(name),
    ),
  );
  const result = spawnSync("sh", ["-c", `. ./${script} && env`], {
    cwd: nginxDir,
    env: { ...inherited, ...env },
    encoding: "utf8",
  });
  const exported = Object.fromEntries(
    result.stdout
      .split("\n")
      .filter((line) => line.includes("="))
      .map((line) => [
        line.slice(0, line.indexOf("=")),
        line.slice(line.indexOf("=") + 1),
      ]),
  );
  return { status: result.status, exported, log: result.stderr };
};

const envsubst = (source: string, exported: Record<string, string>) =>
  source.replace(/\$\{(\w+)\}/g, (match, name: string) =>
    name in exported ? exported[name] : match,
  );

const cspOf = (rendered: string) => {
  const line = rendered
    .split("\n")
    .find((candidate) => candidate.includes("Content-Security-Policy"));
  return line ?? "";
};

const directive = (csp: string, name: string) =>
  csp
    .match(new RegExp(`${name} ([^;"]*)`))?.[1]
    .trim()
    .split(/\s+/) ?? [];

describe("the nginx runtime environment", () => {
  it("only references variables the entrypoint takes care of", () => {
    const referenced = [...template.matchAll(/\$\{(\w+)\}/g)].map(
      (match) => match[1],
    );

    expect(new Set(referenced)).toEqual(new Set(RUNTIME_VARIABLES));
  });

  it("keeps a valid policy and warns when the variables are missing", () => {
    const { status, exported, log } = sourceScript({});
    const csp = cspOf(envsubst(template, exported));

    expect(status).toBe(0);
    expect(csp).not.toContain("${");
    expect(directive(csp, "connect-src")).toEqual(["'self'"]);
    expect(directive(csp, "img-src")).toEqual([
      "'self'",
      "data:",
      "https://static.vseth.ethz.ch",
    ]);
    for (const name of RUNTIME_VARIABLES) {
      expect(log).toContain(`WARN: ${name} is not set`);
    }
  });

  it("treats empty values like missing ones", () => {
    const { exported, log } = sourceScript({
      VISIT_STORAGE_PUBLIC_URL: "",
      VISIT_BACKEND_WEB_URL: "https://visit-api.example.org",
    });
    const csp = cspOf(envsubst(template, exported));

    expect(csp).not.toContain("${");
    expect(log).toContain("WARN: VISIT_STORAGE_PUBLIC_URL is not set");
    expect(log).not.toContain("VISIT_BACKEND_WEB_URL");
    expect(directive(csp, "connect-src")).toEqual([
      "'self'",
      "https://visit-api.example.org",
    ]);
  });

  it("uses configured origins unchanged and stays quiet", () => {
    const { exported, log } = sourceScript({
      VISIT_STORAGE_PUBLIC_URL: "https://s3.example.org",
      VISIT_BACKEND_WEB_URL: "https://visit-api.example.org",
    });
    const csp = cspOf(envsubst(template, exported));

    expect(log).toBe("");
    expect(directive(csp, "img-src")).toContain("https://s3.example.org");
    expect(directive(csp, "connect-src")).toEqual([
      "'self'",
      "https://visit-api.example.org",
    ]);
    expect(directive(csp, "default-src")).toEqual(["'self'"]);
    expect(directive(csp, "frame-ancestors")).toEqual(["'none'"]);
  });
});
