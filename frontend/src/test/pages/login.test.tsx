import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { MockInstance } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import Login from "../../pages/Login";
import * as authState from "../../api/utils";
import { takeLoginNext } from "../../utils/navigation";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { createTestQueryClient, renderWithProviders } from "../render";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";
import { stubLocation, type StubbedLocation } from "../location";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const refreshUrl = `${testBackendUrl}/api/auth/refresh`;
const loginUrl = `${testBackendUrl}/api/auth/login`;
const initiateUrl = `${testBackendUrl}/api/auth/initiate`;

const accessToken = createToken(3600);

let loginBodies: string[] = [];
let refreshRequests = 0;
let clearAuthState: MockInstance<typeof authState.clearAuthState>;
let setToken: MockInstance<typeof authState.setToken>;

beforeEach(() => {
  loginBodies = [];
  refreshRequests = 0;
  clearAuthState = vi.spyOn(authState, "clearAuthState");
  setToken = vi.spyOn(authState, "setToken");
  server.use(
    http.post(refreshUrl, () => {
      refreshRequests += 1;
      return new HttpResponse(null, { status: 401 });
    }),
    http.post(loginUrl, async ({ request }) => {
      loginBodies.push(await request.text());
      return HttpResponse.json({
        access_token: accessToken,
        token_type: "bearer",
      });
    }),
  );
});

describe("Login", () => {
  it("renders the login form", () => {
    renderWithProviders(<Login />);

    expect(
      screen.getByRole("heading", { name: "company.login" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("email.title")).toBeInTheDocument();
    expect(
      screen.getByLabelText("register.password.title"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "login.title" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "keycloak.login" }),
    ).toBeInTheDocument();
  });

  it("resets the client state before storing the new token", async () => {
    const queryClient = createTestQueryClient();
    const clearQueryCache = vi.spyOn(queryClient, "clear");
    const { user } = renderWithProviders(<Login />, { queryClient });

    await user.type(screen.getByLabelText("email.title"), "user@example.com");
    await user.type(
      screen.getByLabelText("register.password.title"),
      "supersecret1",
    );
    await user.click(screen.getByRole("button", { name: "login.title" }));

    await waitFor(() => {
      expect(setToken).toHaveBeenCalledWith(accessToken);
    }, SLOW_WAIT);
    expect(loginBodies).toHaveLength(1);
    expect(loginBodies[0]).toContain("username=user%40example.com");
    expect(clearAuthState).toHaveBeenCalledTimes(1);
    expect(clearQueryCache).toHaveBeenCalledTimes(1);
    expect(clearAuthState.mock.invocationCallOrder[0]).toBeLessThan(
      clearQueryCache.mock.invocationCallOrder[0],
    );
    expect(clearQueryCache.mock.invocationCallOrder[0]).toBeLessThan(
      setToken.mock.invocationCallOrder[0],
    );
  });

  it("keeps invalid credentials on the client", async () => {
    const { user } = renderWithProviders(<Login />);

    await user.type(screen.getByLabelText("email.title"), "not-an-email");
    await user.type(screen.getByLabelText("register.password.title"), "short");
    await user.click(screen.getByRole("button", { name: "login.title" }));

    expect(
      await screen.findByText("email.valid", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(screen.getByText("password.min")).toBeInTheDocument();
    expect(loginBodies).toHaveLength(0);
    expect(setToken).not.toHaveBeenCalled();
  });

  it("trims whitespace an autocomplete adds to the email", async () => {
    const { user } = renderWithProviders(<Login />);

    await user.type(screen.getByLabelText("email.title"), "user@example.com ");
    await user.type(
      screen.getByLabelText("register.password.title"),
      "supersecret1",
    );
    await user.click(screen.getByRole("button", { name: "login.title" }));

    await waitFor(() => expect(loginBodies).toHaveLength(1), SLOW_WAIT);
    expect(loginBodies[0]).toContain("username=user%40example.com&");
  });

  it("does not refresh a session that does not exist", async () => {
    const { user } = renderWithProviders(<Login />);

    await user.type(screen.getByLabelText("email.title"), "user@example.com");
    await user.type(
      screen.getByLabelText("register.password.title"),
      "supersecret1",
    );
    await user.click(screen.getByRole("button", { name: "login.title" }));

    await waitFor(() => expect(loginBodies).toHaveLength(1), SLOW_WAIT);
    expect(refreshRequests).toBe(0);
  });
});

describe("Login with Keycloak", () => {
  let location: StubbedLocation;

  beforeEach(() => {
    location = stubLocation("/login");
    server.use(
      http.get(initiateUrl, () =>
        HttpResponse.json("https://idp.example/auth"),
      ),
    );
  });

  afterEach(() => {
    location.restore();
    sessionStorage.clear();
  });

  it("remembers the requested page for after the sign-in", async () => {
    const { user } = renderWithProviders(<Login />, {
      route: "/login?next=%2Fcompany%2Fjoin%2Ftok",
    });

    await user.click(screen.getByRole("button", { name: "keycloak.login" }));

    await waitFor(() =>
      expect(location.navigations).toEqual(["https://idp.example/auth"]),
    );
    expect(takeLoginNext()).toBe("/company/join/tok");
  });
});
