import { beforeEach, describe, expect, it } from "vitest";
import { act, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import App from "../../App";
import { isImpersonating, setImpersonation, setToken } from "../../api/utils";
import { getGetCurrentUserQueryKey } from "../../orval/generated/user/user";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { createTestQueryClient, renderWithProviders } from "../render";

const refreshUrl = `${testBackendUrl}/api/auth/refresh`;
const meUrl = `${testBackendUrl}/api/user/me`;
const profileUrl = `${testBackendUrl}/api/user/profile`;

const currentUser = {
  id: "user-1",
  email: "user@example.com",
  first_name: "Jane",
  last_name: "Doe",
  is_staff: false,
  is_admin: false,
  is_company: true,
  company_id: "company-1",
  email_confirmed: true,
};

let meRequests = 0;

const storageEventFromAnotherTab = () => {
  act(() => {
    window.dispatchEvent(new StorageEvent("storage", { key: "token" }));
  });
};

const signOutInAnotherTab = () => {
  localStorage.removeItem("token");
  storageEventFromAnotherTab();
};

const renderApp = async () => {
  const queryClient = createTestQueryClient();
  renderWithProviders(<App />, { route: "/not-allowed", queryClient });

  await waitFor(() => {
    expect(queryClient.getQueryData(getGetCurrentUserQueryKey())).toEqual(
      currentUser,
    );
  });
  expect(meRequests).toBe(1);

  return queryClient;
};

beforeEach(() => {
  meRequests = 0;
  setToken(createToken(3600, "alice"));
  server.use(
    http.post(refreshUrl, () => new HttpResponse(null, { status: 401 })),
    http.get(meUrl, () => {
      meRequests += 1;
      return HttpResponse.json(currentUser);
    }),
  );
});

describe("token sync between tabs", () => {
  it("drops the cached current user when another tab signs out", async () => {
    const queryClient = await renderApp();

    signOutInAnotherTab();

    await waitFor(() => {
      expect(
        queryClient.getQueryData(getGetCurrentUserQueryKey()),
      ).toBeUndefined();
    });
  });

  it("drops the previous user's data when another tab signs in as someone else", async () => {
    const subjectOf = (request: Request) =>
      request.headers.get("Authorization")?.endsWith(bobToken)
        ? "bob@example.com"
        : "alice@example.com";
    const bobToken = createToken(3600, "bob");
    server.use(
      http.get(profileUrl, ({ request }) =>
        HttpResponse.json({ ...currentUser, email: subjectOf(request) }),
      ),
    );
    renderWithProviders(<App />, { route: "/profile" });
    expect(await screen.findByText("alice@example.com")).toBeInTheDocument();

    localStorage.setItem("token", bobToken);
    storageEventFromAnotherTab();

    expect(await screen.findByText("bob@example.com")).toBeInTheDocument();
    expect(screen.queryByText("alice@example.com")).not.toBeInTheDocument();
  });

  it("clears the impersonation when another tab signs out", async () => {
    await renderApp();
    setImpersonation("42", "Jane Doe");

    signOutInAnotherTab();

    expect(isImpersonating()).toBe(false);
  });

  it("refetches the current user and keeps the impersonation while a token remains", async () => {
    await renderApp();
    setImpersonation("42", "Jane Doe");

    storageEventFromAnotherTab();

    expect(isImpersonating()).toBe(true);
    await waitFor(() => {
      expect(meRequests).toBe(2);
    });
    expect(screen.getByText("not_allowed.title")).toBeInTheDocument();
  });
});
