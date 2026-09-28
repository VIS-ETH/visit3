import { beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";

const csrfUrl = `${testBackendUrl}/api/csrftoken`;

let issuedTokens = 0;

const importUtils = () => import("../../api/utils");

const dispatchStorageEvent = (key: string | null) => {
  window.dispatchEvent(new StorageEvent("storage", { key }));
};

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

describe("token storage", () => {
  it("stores, reads and removes the token in localStorage", async () => {
    const { clearToken, getToken, setToken } = await importUtils();
    const token = createToken(3600);

    expect(getToken()).toBeNull();

    setToken(token);
    expect(localStorage.getItem("token")).toBe(token);
    expect(getToken()).toBe(token);

    clearToken();
    expect(localStorage.getItem("token")).toBeNull();
    expect(getToken()).toBeNull();
  });

  it("announces token changes in the current tab", async () => {
    const { clearToken, setToken } = await importUtils();
    const onChange = vi.fn();
    window.addEventListener("auth-token-changed", onChange);

    setToken(createToken(3600));
    clearToken();

    expect(onChange).toHaveBeenCalledTimes(2);
    window.removeEventListener("auth-token-changed", onChange);
  });
});

describe("subscribeToTokenStorage", () => {
  it("reacts to token changes from another tab", async () => {
    const { subscribeToTokenStorage } = await importUtils();
    const onTokenChanged = vi.fn();
    const unsubscribe = subscribeToTokenStorage(onTokenChanged);

    localStorage.setItem("token", createToken(3600));
    dispatchStorageEvent("token");

    expect(onTokenChanged).toHaveBeenCalledTimes(1);
    unsubscribe();
  });

  it("clears impersonation when the token is gone", async () => {
    const { isImpersonating, setImpersonation, subscribeToTokenStorage } =
      await importUtils();
    setImpersonation("42", "Jane Doe");
    const onTokenChanged = vi.fn();
    const unsubscribe = subscribeToTokenStorage(onTokenChanged);

    dispatchStorageEvent("token");

    expect(isImpersonating()).toBe(false);
    expect(sessionStorage.getItem("impersonating_display_name")).toBeNull();
    expect(onTokenChanged).toHaveBeenCalledTimes(1);
    unsubscribe();
  });

  it("keeps impersonation while a token is stored", async () => {
    const { isImpersonating, setImpersonation, subscribeToTokenStorage } =
      await importUtils();
    setImpersonation("42", "Jane Doe");
    localStorage.setItem("token", createToken(3600));
    const unsubscribe = subscribeToTokenStorage(vi.fn());

    dispatchStorageEvent("token");

    expect(isImpersonating()).toBe(true);
    unsubscribe();
  });

  it("ignores changes to other storage keys", async () => {
    const { isImpersonating, setImpersonation, subscribeToTokenStorage } =
      await importUtils();
    setImpersonation("42", "Jane Doe");
    const onTokenChanged = vi.fn();
    const unsubscribe = subscribeToTokenStorage(onTokenChanged);

    dispatchStorageEvent("colorScheme");

    expect(onTokenChanged).not.toHaveBeenCalled();
    expect(isImpersonating()).toBe(true);
    unsubscribe();
  });

  it("reacts to a full storage clear", async () => {
    const { subscribeToTokenStorage } = await importUtils();
    const onTokenChanged = vi.fn();
    const unsubscribe = subscribeToTokenStorage(onTokenChanged);

    dispatchStorageEvent(null);

    expect(onTokenChanged).toHaveBeenCalledTimes(1);
    unsubscribe();
  });

  it("stops listening once unsubscribed", async () => {
    const { subscribeToTokenStorage } = await importUtils();
    const onTokenChanged = vi.fn();

    subscribeToTokenStorage(onTokenChanged)();
    dispatchStorageEvent("token");

    expect(onTokenChanged).not.toHaveBeenCalled();
  });
});

describe("clearAuthState", () => {
  it("drops the token, the impersonation and the csrf cache", async () => {
    const {
      clearAuthState,
      getCsrfToken,
      isImpersonating,
      getToken,
      setImpersonation,
      setToken,
    } = await importUtils();
    setToken(createToken(3600));
    setImpersonation("42", "Jane Doe");
    expect(await getCsrfToken()).toBe("csrf-1");

    clearAuthState();

    expect(getToken()).toBeNull();
    expect(isImpersonating()).toBe(false);
    expect(await getCsrfToken()).toBe("csrf-2");
  });

  it("announces the token change", async () => {
    const { clearAuthState, setToken } = await importUtils();
    setToken(createToken(3600));
    const onChange = vi.fn();
    window.addEventListener("auth-token-changed", onChange);

    clearAuthState();

    expect(onChange).toHaveBeenCalledTimes(1);
    window.removeEventListener("auth-token-changed", onChange);
  });
});
