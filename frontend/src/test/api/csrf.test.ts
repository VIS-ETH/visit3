import { beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../server";
import { testBackendUrl } from "../constants";

const csrfUrl = `${testBackendUrl}/api/csrftoken`;

let issuedTokens = 0;

const importUtils = () => import("../../api/utils");

beforeEach(() => {
  vi.resetModules();
  issuedTokens = 0;
  server.use(
    http.get(csrfUrl, () => {
      issuedTokens += 1;
      return HttpResponse.json({ token: `csrf-${issuedTokens}` });
    }),
  );
});

describe("getCsrfToken", () => {
  it("fetches once and serves the cached token afterwards", async () => {
    const { getCsrfToken } = await importUtils();

    expect(await getCsrfToken()).toBe("csrf-1");
    expect(await getCsrfToken()).toBe("csrf-1");
    expect(issuedTokens).toBe(1);
  });

  it("shares a single fetch between concurrent callers", async () => {
    const { getCsrfToken } = await importUtils();

    const tokens = await Promise.all([
      getCsrfToken(),
      getCsrfToken(),
      getCsrfToken(),
    ]);

    expect(tokens).toEqual(["csrf-1", "csrf-1", "csrf-1"]);
    expect(issuedTokens).toBe(1);
  });

  it("fetches again after a failed fetch", async () => {
    server.use(
      http.get(csrfUrl, () => new HttpResponse(null, { status: 500 }), {
        once: true,
      }),
    );
    const { getCsrfToken } = await importUtils();

    await expect(getCsrfToken()).rejects.toThrow();
    expect(await getCsrfToken()).toBe("csrf-1");
  });
});

describe("renewCsrfToken", () => {
  it("refetches and replaces the cached token", async () => {
    const { getCsrfToken, renewCsrfToken } = await importUtils();

    expect(await getCsrfToken()).toBe("csrf-1");
    expect(await renewCsrfToken()).toBe("csrf-2");
    expect(await getCsrfToken()).toBe("csrf-2");
    expect(issuedTokens).toBe(2);
  });

  it("refetches on every call", async () => {
    const { renewCsrfToken } = await importUtils();

    expect(await renewCsrfToken()).toBe("csrf-1");
    expect(await renewCsrfToken()).toBe("csrf-2");
    expect(issuedTokens).toBe(2);
  });

  it("shares a single fetch between concurrent callers", async () => {
    const { renewCsrfToken } = await importUtils();

    const tokens = await Promise.all([
      renewCsrfToken(),
      renewCsrfToken(),
      renewCsrfToken(),
    ]);

    expect(tokens).toEqual(["csrf-1", "csrf-1", "csrf-1"]);
    expect(issuedTokens).toBe(1);
  });

  it("serves the renewed token to later callers", async () => {
    const { getCsrfToken, renewCsrfToken } = await importUtils();

    const [renewed, cached] = await Promise.all([
      renewCsrfToken(),
      renewCsrfToken(),
    ]);

    expect(renewed).toBe("csrf-1");
    expect(cached).toBe("csrf-1");
    expect(await getCsrfToken()).toBe("csrf-1");
    expect(issuedTokens).toBe(1);
  });
});

describe("clearCsrfToken", () => {
  it("drops the cached token", async () => {
    const { clearCsrfToken, getCsrfToken } = await importUtils();

    expect(await getCsrfToken()).toBe("csrf-1");
    clearCsrfToken();

    expect(await getCsrfToken()).toBe("csrf-2");
    expect(issuedTokens).toBe(2);
  });
});
