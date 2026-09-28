import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import Login from "../../pages/Login";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { renderWithProviders } from "../render";

beforeEach(() => {
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.post(`${testBackendUrl}/api/auth/refresh`, () =>
      HttpResponse.json(null, { status: 401 }),
    ),
  );
});

describe("Login with a keycloak callback error", () => {
  it("translates a refused membership", () => {
    renderWithProviders(<Login />, {
      route: "/login?error=auth.not_vis_member",
    });

    expect(screen.getByText("auth.not_vis_member")).toBeInTheDocument();
  });

  it("translates an email that belongs to a local account", () => {
    renderWithProviders(<Login />, {
      route: "/login?error=auth.email_taken_locally",
    });

    expect(screen.getByText("auth.email_taken_locally")).toBeInTheDocument();
  });

  it("falls back to a generic message for unknown codes", () => {
    renderWithProviders(<Login />, {
      route: "/login?error=common.welcome",
    });

    expect(screen.getByText("server.error")).toBeInTheDocument();
    expect(screen.queryByText("common.welcome")).not.toBeInTheDocument();
  });

  it("shows no error banner without an error parameter", () => {
    renderWithProviders(<Login />, { route: "/login" });

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
