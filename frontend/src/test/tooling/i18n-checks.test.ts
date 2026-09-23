import { describe, expect, it } from "vitest";
import { spawnSync } from "node:child_process";
import path from "node:path";

const frontendRoot = process.cwd();
const fixtureRoot = path.join(frontendRoot, "src", "test", "fixtures", "i18n");

const literalsScript = path.join(
  frontendRoot,
  "scripts",
  "check-i18n-literals.mjs",
);
const keysScript = path.join(frontendRoot, "scripts", "check-i18n-keys.mjs");

const runCheck = (script: string, fixture: string) => {
  const result = spawnSync(
    process.execPath,
    [script, path.join(fixtureRoot, fixture)],
    { encoding: "utf8" },
  );

  return {
    status: result.status,
    output: `${result.stdout}${result.stderr}`,
  };
};

describe("check-i18n-literals", () => {
  it("names the offending file and every untranslated literal", () => {
    const { status, output } = runCheck(literalsScript, "bad");

    expect(status).toBe(1);
    expect(output).toContain(path.join("src", "BoothCard.tsx"));
    expect(output).toContain(
      "Every booth comes with a table and two chairs, and the power socket is billed separately.",
    );
    expect(output).toContain("Photo of a booth");
    expect(output).toContain("Booth number");
    expect(output).toContain("Pick a booth number");
    expect(output).toContain("Booth saved");
  });

  it("accepts a fully translated file", () => {
    const { status, output } = runCheck(literalsScript, "good");

    expect(status).toBe(0);
    expect(output).toContain("no obvious hardcoded user-facing literals");
  });

  it("skips the fixtures when it runs over the real sources", () => {
    const result = spawnSync(process.execPath, [literalsScript], {
      cwd: frontendRoot,
      encoding: "utf8",
    });

    expect(result.status).toBe(0);
  });
});

describe("check-i18n-keys", () => {
  it("reports referenced keys and locale keys that are missing", () => {
    const { status, output } = runCheck(keysScript, "bad");

    expect(status).toBe(1);
    expect(output).toContain("fixture.missing_title");
    expect(output).toContain("fixture.only_in_en");
  });

  it("accepts a fixture whose keys exist in both locales", () => {
    const { status, output } = runCheck(keysScript, "good");

    expect(status).toBe(0);
    expect(output).toContain("all referenced translation keys exist");
  });

  it("skips template-literal keys and reports how many it skipped", () => {
    const { status, output } = runCheck(keysScript, "dynamic");

    expect(status).toBe(0);
    expect(output).toContain("skipped 2 dynamic translation keys");
    expect(output).not.toContain("fixture.status_");
    expect(output).not.toContain("fixture.profile_field.");
  });

  it("skips the fixtures when it runs over the real sources", () => {
    const result = spawnSync(process.execPath, [keysScript], {
      cwd: frontendRoot,
      encoding: "utf8",
    });

    expect(result.status).toBe(0);
  });
});
