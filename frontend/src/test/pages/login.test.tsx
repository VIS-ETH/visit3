import { beforeEach, describe, expect, it, vi } from "vitest";
import type { MockInstance } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import Login from "../../pages/Login";
import * as authState from "../../api/utils";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { createTestQueryClient, renderWithProviders } from "../render";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const csrfUrl = `${testBackendUrl}/api/csrftoken`;
const refreshUrl = `${testBackendUrl}/api/auth/refresh`;
const loginUrl = `${testBackendUrl}/api/auth/login`;

const accessToken = createToken(3600);

let loginBodies: string[] = [];
let clearAuthState: MockInstance<typeof authState.clearAuthState>;
let setToken: MockInstance<typeof authState.setToken>;

beforeEach(() => {
  loginBodies = [];
  clearAuthState = vi.spyOn(authState, "clearAuthState");
  setToken = vi.spyOn(authState, "setToken");
  server.use(
    http.get(csrfUrl, () => HttpResponse.json({ token: "csrf-1" })),
    http.post(refreshUrl, () => new HttpResponse(null, { status: 401 })),
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
});
