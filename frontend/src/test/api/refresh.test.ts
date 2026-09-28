import { beforeEach, describe, expect, it, vi } from "vitest";
import { delay, http, HttpResponse } from "msw";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";

const csrfUrl = `${testBackendUrl}/api/csrftoken`;
const refreshUrl = `${testBackendUrl}/api/auth/refresh`;

const importUtils = () => import("../../api/utils");

let csrfRequests = 0;
let refreshRequests = 0;
let refreshedToken = "";

const respondWithRefreshedToken = () => {
  server.use(
    http.post(refreshUrl, () => {
      refreshRequests += 1;
      return HttpResponse.json({
        access_token: refreshedToken,
        token_type: "bearer",
      });
    }),
  );
};

const createDeferred = () => {
  let resolve: () => void = () => {};
  const promise = new Promise<void>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
};

beforeEach(() => {
  vi.resetModules();
  csrfRequests = 0;
  refreshRequests = 0;
  refreshedToken = createToken(3600, "user-refreshed");
  server.use(
    http.get(csrfUrl, async () => {
      csrfRequests += 1;
      await delay(10);
      return HttpResponse.json({ token: `csrf-${csrfRequests}` });
    }),
  );
});

describe("refreshToken", () => {
  it("stores the refreshed access token", async () => {
    respondWithRefreshedToken();
    const { refreshToken, getToken } = await importUtils();

    expect(await refreshToken()).toBe(refreshedToken);
    expect(getToken()).toBe(refreshedToken);
    expect(refreshRequests).toBe(1);
  });

  it("sends the csrf token with the refresh request", async () => {
    const refreshHeaders: (string | null)[] = [];
    server.use(
      http.post(refreshUrl, ({ request }) => {
        refreshRequests += 1;
        refreshHeaders.push(request.headers.get("X-CSRF-Token"));
        return HttpResponse.json({
          access_token: refreshedToken,
          token_type: "bearer",
        });
      }),
    );
    const { refreshToken } = await importUtils();

    await refreshToken();

    expect(refreshHeaders).toEqual(["csrf-1"]);
  });

  it("refreshes once for callers that start in the same tick", async () => {
    respondWithRefreshedToken();
    const { refreshToken } = await importUtils();

    const tokens = await Promise.all([refreshToken(), refreshToken()]);

    expect(tokens).toEqual([refreshedToken, refreshedToken]);
    expect(refreshRequests).toBe(1);
    expect(csrfRequests).toBe(1);
  });

  it("refreshes once for callers that start while the request is in flight", async () => {
    const requestReceived = createDeferred();
    const responseReleased = createDeferred();
    server.use(
      http.post(refreshUrl, async () => {
        refreshRequests += 1;
        requestReceived.resolve();
        await responseReleased.promise;
        return HttpResponse.json({
          access_token: refreshedToken,
          token_type: "bearer",
        });
      }),
    );
    const { refreshToken } = await importUtils();

    const first = refreshToken();
    await requestReceived.promise;
    const second = refreshToken();
    responseReleased.resolve();

    expect(await Promise.all([first, second])).toEqual([
      refreshedToken,
      refreshedToken,
    ]);
    expect(refreshRequests).toBe(1);
  });

  it("refreshes again once the previous refresh has settled", async () => {
    respondWithRefreshedToken();
    const { refreshToken } = await importUtils();

    await refreshToken();
    await refreshToken();

    expect(refreshRequests).toBe(2);
  });

  it("clears the auth state and resolves to null when the refresh fails", async () => {
    server.use(
      http.post(refreshUrl, () => {
        refreshRequests += 1;
        return new HttpResponse(null, { status: 401 });
      }),
    );
    const { getToken, isImpersonating, refreshToken, setImpersonation } =
      await importUtils();
    setImpersonation("42", "Jane Doe");

    const tokens = await Promise.all([refreshToken(), refreshToken()]);

    expect(tokens).toEqual([null, null]);
    expect(refreshRequests).toBe(1);
    expect(getToken()).toBeNull();
    expect(isImpersonating()).toBe(false);
  });
});
