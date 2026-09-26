import { File as NodeFile } from "node:buffer";
import { Fragment, createElement } from "react";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { delay, http, HttpResponse } from "msw";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { stubLocation, type StubbedLocation } from "../location";
import { notificationsShow } from "../notifications";

const csrfUrl = `${testBackendUrl}/api/csrftoken`;
const refreshUrl = `${testBackendUrl}/api/auth/refresh`;
const meUrl = `${testBackendUrl}/api/user/me`;
const profileUrl = `${testBackendUrl}/api/user/profile`;

const csrfError = () =>
  HttpResponse.json(
    { code: "csrf.validation_failed", message: "CSRF token invalid" },
    { status: 403 },
  );

const unauthorized = () =>
  HttpResponse.json({ detail: "Not authenticated" }, { status: 401 });

let csrfRequests = 0;
let refreshRequests = 0;
let meRequests: Request[] = [];
let location: StubbedLocation;

const importApi = async () => (await import("../../api/interceptor")).default;

const storeValidToken = () => {
  const token = createToken(3600);
  localStorage.setItem("token", token);
  return token;
};

const respondWithRefreshedToken = (token: string, delayInMs = 0) => {
  server.use(
    http.post(refreshUrl, async () => {
      refreshRequests += 1;
      if (delayInMs) await delay(delayInMs);
      return HttpResponse.json({ access_token: token, token_type: "bearer" });
    }),
  );
};

const respondWithFailingRefresh = () => {
  server.use(
    http.post(refreshUrl, () => {
      refreshRequests += 1;
      return unauthorized();
    }),
  );
};

beforeEach(() => {
  vi.resetModules();
  csrfRequests = 0;
  refreshRequests = 0;
  meRequests = [];
  location = stubLocation("/");
  server.use(
    http.get(csrfUrl, () => {
      csrfRequests += 1;
      return HttpResponse.json({ token: `csrf-${csrfRequests}` });
    }),
  );
});

afterEach(() => {
  location.restore();
});

describe("csrf recovery", () => {
  it("renews the token once and replays the request", async () => {
    storeValidToken();
    server.use(
      http.get(meUrl, ({ request }) => {
        meRequests.push(request);
        if (meRequests.length === 1) return csrfError();
        return HttpResponse.json({ id: "user-1" });
      }),
    );
    const api = await importApi();

    const response = await api.get("/api/user/me");

    expect(response.data).toEqual({ id: "user-1" });
    expect(csrfRequests).toBe(2);
    expect(meRequests).toHaveLength(2);
    expect(meRequests[0].headers.get("X-CSRF-Token")).toBe("csrf-1");
    expect(meRequests[1].headers.get("X-CSRF-Token")).toBe("csrf-2");
    expect(notificationsShow).not.toHaveBeenCalled();
    expect(location.navigations).toEqual([]);
  });

  it("notifies without redirecting when the renewed token fails too", async () => {
    storeValidToken();
    server.use(
      http.get(meUrl, ({ request }) => {
        meRequests.push(request);
        return csrfError();
      }),
    );
    const api = await importApi();

    await expect(api.get("/api/user/me")).rejects.toThrow();

    expect(meRequests).toHaveLength(2);
    expect(csrfRequests).toBe(2);
    expect(notificationsShow).toHaveBeenCalledTimes(1);
    expect(notificationsShow).toHaveBeenCalledWith(
      expect.objectContaining({
        color: "red",
        title: "error.title",
        message: "CSRF token invalid",
      }),
    );
    expect(location.navigations).toEqual([]);
  });
});

describe("token refresh on 401", () => {
  it("refreshes once and replays the request with the new token", async () => {
    storeValidToken();
    const refreshedToken = createToken(3600, "user-refreshed");
    respondWithRefreshedToken(refreshedToken);
    server.use(
      http.get(meUrl, ({ request }) => {
        meRequests.push(request);
        if (meRequests.length === 1) return unauthorized();
        return HttpResponse.json({ id: "user-1" });
      }),
    );
    const api = await importApi();

    const response = await api.get("/api/user/me");

    expect(response.data).toEqual({ id: "user-1" });
    expect(refreshRequests).toBe(1);
    expect(meRequests).toHaveLength(2);
    expect(meRequests[1].headers.get("Authorization")).toBe(
      `Bearer ${refreshedToken}`,
    );
    expect(localStorage.getItem("token")).toBe(refreshedToken);
    expect(location.navigations).toEqual([]);
  });

  it("clears the auth state and redirects when the refresh fails", async () => {
    storeValidToken();
    respondWithFailingRefresh();
    server.use(
      http.get(meUrl, ({ request }) => {
        meRequests.push(request);
        return unauthorized();
      }),
    );
    const api = await importApi();

    await expect(api.get("/api/user/me")).rejects.toThrow();

    expect(refreshRequests).toBe(1);
    expect(meRequests).toHaveLength(1);
    expect(localStorage.getItem("token")).toBeNull();
    expect(location.navigations).toEqual(["/login"]);
    expect(notificationsShow).not.toHaveBeenCalled();
  });

  it("shares a single refresh between concurrent failures", async () => {
    storeValidToken();
    respondWithRefreshedToken(createToken(3600, "user-refreshed"), 50);
    const profileRequests: Request[] = [];
    server.use(
      http.get(meUrl, ({ request }) => {
        meRequests.push(request);
        if (meRequests.length === 1) return unauthorized();
        return HttpResponse.json({ id: "user-1" });
      }),
      http.get(profileUrl, ({ request }) => {
        profileRequests.push(request);
        if (profileRequests.length === 1) return unauthorized();
        return HttpResponse.json({ id: "profile-1" });
      }),
    );
    const api = await importApi();

    const responses = await Promise.all([
      api.get("/api/user/me"),
      api.get("/api/user/profile"),
    ]);

    expect(responses.map((response) => response.data)).toEqual([
      { id: "user-1" },
      { id: "profile-1" },
    ]);
    expect(refreshRequests).toBe(1);
    expect(meRequests).toHaveLength(2);
    expect(profileRequests).toHaveLength(2);
  });

  it("does not redirect when the login page is already open", async () => {
    location.restore();
    location = stubLocation("/login");
    storeValidToken();
    respondWithFailingRefresh();
    server.use(
      http.get(meUrl, ({ request }) => {
        meRequests.push(request);
        return unauthorized();
      }),
    );
    const api = await importApi();

    await expect(api.get("/api/user/me")).rejects.toThrow();

    expect(localStorage.getItem("token")).toBeNull();
    expect(location.navigations).toEqual([]);
  });

  it("does not replay the request when no token is stored", async () => {
    respondWithFailingRefresh();
    server.use(
      http.get(meUrl, ({ request }) => {
        meRequests.push(request);
        return unauthorized();
      }),
    );
    const api = await importApi();

    await expect(api.get("/api/user/me")).rejects.toThrow();

    expect(refreshRequests).toBe(1);
    expect(meRequests).toHaveLength(1);
    expect(meRequests[0].headers.get("Authorization")).toBeNull();
    expect(location.navigations).toEqual(["/login"]);
  });
});

describe("quiet statuses", () => {
  const rateLimited = () =>
    HttpResponse.json(
      { code: "error.rate_limited", message: "Too many requests" },
      { status: 429 },
    );

  it("rejects without a notification for a status the request expects", async () => {
    storeValidToken();
    server.use(http.get(meUrl, rateLimited));
    const api = await importApi();

    await expect(
      api.get("/api/user/me", { quietStatuses: [429] }),
    ).rejects.toThrow();

    expect(notificationsShow).not.toHaveBeenCalled();
  });

  it("still notifies about other statuses", async () => {
    storeValidToken();
    server.use(http.get(meUrl, rateLimited));
    const api = await importApi();

    await expect(
      api.get("/api/user/me", { quietStatuses: [409] }),
    ).rejects.toThrow();

    expect(notificationsShow).toHaveBeenCalledTimes(1);
  });
});

describe("upload failures", () => {
  const logoUrl = `${testBackendUrl}/api/company/me/profile/logo`;

  const uploadLogo = async () => {
    const api = await importApi();
    const form = new FormData();
    form.append(
      "file",
      new NodeFile(["logo"], "logo.png", {
        type: "image/png",
      }) as unknown as File,
    );
    return api.post("/api/company/me/profile/logo", form);
  };

  const shownMessage = () =>
    (notificationsShow.mock.calls.at(-1)?.[0] as { message: string }).message;

  it("explains a proxy that rejects the file as too large", async () => {
    storeValidToken();
    server.use(
      http.post(logoUrl, () => new HttpResponse("Too Large", { status: 413 })),
    );

    await expect(uploadLogo()).rejects.toThrow();

    expect(shownMessage()).toBe("error.storage_file_too_large");
  });

  it("explains an upload the network dropped before it reached the server", async () => {
    storeValidToken();
    server.use(http.post(logoUrl, () => HttpResponse.error()));

    await expect(uploadLogo()).rejects.toThrow();

    expect(shownMessage()).toBe("error.upload_rejected");
  });

  it("keeps the network message for other requests the network dropped", async () => {
    storeValidToken();
    server.use(http.get(meUrl, () => HttpResponse.error()));
    const api = await importApi();

    await expect(api.get("/api/user/me")).rejects.toThrow();

    expect(shownMessage()).toBe("error.network");
  });
});

describe("unexpected failures", () => {
  const lastNotification = () =>
    notificationsShow.mock.calls.at(-1)?.[0] as {
      message: unknown;
    };

  it("shows the error id of an unexpected server error", async () => {
    storeValidToken();
    server.use(
      http.get(meUrl, () =>
        HttpResponse.json(
          {
            statusCode: 500,
            code: "error.internal",
            message: "Internal server error",
            requestId: "abc123def456",
          },
          { status: 500 },
        ),
      ),
    );
    const api = await importApi();

    await expect(api.get("/api/user/me")).rejects.toThrow();

    render(createElement(Fragment, null, lastNotification().message as never));
    expect(screen.getByText(/abc123def456/)).toBeInTheDocument();
  });

  it("explains a request the network dropped", async () => {
    storeValidToken();
    server.use(http.get(meUrl, () => HttpResponse.error()));
    const api = await importApi();

    await expect(api.get("/api/user/me")).rejects.toThrow();

    expect(lastNotification().message).toBe("error.network");
  });
});
