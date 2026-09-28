import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

const template = fs.readFileSync(
  path.join(process.cwd(), "nginx", "default.conf.template"),
  "utf8",
);

const headerValue = (name: string) => {
  const match = template.match(
    new RegExp(`add_header ${name} "([^"]*)" always;`),
  );
  return match?.[1];
};

const policy = () =>
  Object.fromEntries(
    (headerValue("Content-Security-Policy") ?? "")
      .split(";")
      .map((directive) => directive.trim().split(/\s+/))
      .map(([name, ...sources]) => [name, sources]),
  );

describe("nginx security headers", () => {
  it("hides the nginx version", () => {
    expect(template).toContain("server_tokens off;");
  });

  it("forbids framing, sniffing and leaking full referrers", () => {
    expect(headerValue("X-Frame-Options")).toBe("DENY");
    expect(headerValue("X-Content-Type-Options")).toBe("nosniff");
    expect(headerValue("Referrer-Policy")).toBe(
      "strict-origin-when-cross-origin",
    );
    expect(headerValue("Permissions-Policy")).toContain("camera=()");
  });

  it("allows scripts only from the app and the VSETH theme host", () => {
    expect(policy()["script-src"]).toEqual([
      "'self'",
      "https://static.vseth.ethz.ch",
    ]);
    expect(template).not.toContain("unsafe-eval");
  });

  it("takes the backend and storage origins from the environment", () => {
    expect(policy()["connect-src"]).toEqual([
      "'self'",
      "${VISIT_BACKEND_WEB_URL}",
    ]);
    expect(policy()["img-src"]).toContain("${VISIT_STORAGE_PUBLIC_URL}");
  });

  it("locks down plugins, base urls, forms and frame ancestors", () => {
    expect(policy()["object-src"]).toEqual(["'none'"]);
    expect(policy()["base-uri"]).toEqual(["'self'"]);
    expect(policy()["form-action"]).toEqual(["'self'"]);
    expect(policy()["frame-ancestors"]).toEqual(["'none'"]);
  });
});
