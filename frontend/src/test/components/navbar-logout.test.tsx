import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { AppShell } from "@mantine/core";
import Navbar from "../../components/Navbar";
import { UserProvider } from "../../context/UserContext";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";

const logoutUrl = `${testBackendUrl}/api/user/logout`;

let logoutRequests = 0;

const renderNavbar = () =>
  renderWithProviders(
    <UserProvider user={undefined} isLoading={false}>
      <AppShell>
        <Navbar />
      </AppShell>
    </UserProvider>,
  );

const logoutButton = () => screen.getByRole("button", { name: "nav.logout" });

beforeEach(() => {
  logoutRequests = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.post(logoutUrl, () => {
      logoutRequests += 1;
      return HttpResponse.json({});
    }),
  );
});

describe("navbar logout", () => {
  it("asks for confirmation before logging out", async () => {
    const { user } = renderNavbar();

    await user.click(logoutButton());

    expect(screen.getByText("nav.logout_confirm_body")).toBeInTheDocument();
    expect(logoutRequests).toBe(0);
  });

  it("stays signed in when the confirmation is dismissed", async () => {
    const { user } = renderNavbar();

    await user.click(logoutButton());
    await user.click(screen.getByRole("button", { name: "common.cancel" }));

    expect(logoutRequests).toBe(0);
    expect(
      screen.queryByText("nav.logout_confirm_body"),
    ).not.toBeInTheDocument();
  });

  it("logs out once the confirmation is accepted", async () => {
    const { user } = renderNavbar();

    await user.click(logoutButton());
    await user.click(
      screen.getByRole("button", { name: "nav.logout_confirm_submit" }),
    );

    await waitFor(() => {
      expect(logoutRequests).toBe(1);
    });
  });
});
