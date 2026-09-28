import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router";
import AuthLink from "../../pages/AuthLink";
import Login from "../../pages/Login";
import { testBackendUrl } from "../constants";
import { stubLocation, type StubbedLocation } from "../location";
import { renderWithProviders } from "../render";

const token = "magic-token-123";

let location: StubbedLocation;

const renderAuthLink = (route: string) =>
  renderWithProviders(
    <Routes>
      <Route path="/auth/link/:token" element={<AuthLink />} />
    </Routes>,
    { route },
  );

beforeEach(() => {
  location = stubLocation("/auth/link/magic-token-123");
});

afterEach(() => {
  location.restore();
});

describe("magic link landing", () => {
  it("forwards the browser to the backend link endpoint", () => {
    renderAuthLink(`/auth/link/${token}`);

    expect(location.navigations).toEqual([
      `${testBackendUrl}/api/auth/link/${token}`,
    ]);
  });

  it("escapes a token with url unsafe characters", () => {
    renderAuthLink("/auth/link/a%2Fb");

    expect(location.navigations).toEqual([
      `${testBackendUrl}/api/auth/link/a%2Fb`,
    ]);
  });

  it("keeps the user informed while redirecting", () => {
    renderAuthLink(`/auth/link/${token}`);

    expect(screen.getByText("auth.link_redirecting")).toBeInTheDocument();
  });
});

describe("login after an invalid magic link", () => {
  it("explains the rejected link instead of a generic error", () => {
    renderWithProviders(<Login />, {
      route: "/login?error=auth.link_invalid",
    });

    expect(screen.getByText("auth.link_invalid")).toBeInTheDocument();
    expect(screen.queryByText("server.error")).not.toBeInTheDocument();
  });
});
