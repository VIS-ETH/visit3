import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import UserManagement from "../../pages/UserManagement";
import RootLayout from "../../pages/root";
import { UserProvider } from "../../context/UserContext";
import {
  getGetAllStaffQueryKey,
  useGetCurrentUser,
} from "../../orval/generated/user/user";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { setImpersonation } from "../../api/utils";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { QueryClient } from "@tanstack/react-query";
import { renderWithProviders } from "../render";

const createCachingQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 60_000 },
      mutations: { retry: false },
    },
  });

const adminUser: UserResponse = {
  id: "admin-1",
  email: "admin@example.com",
  is_staff: true,
  is_admin: true,
  is_company: false,
  is_kp_president: true,
  user_confirmed: true,
  email_confirmed: true,
};

const companyUser = {
  id: "user-9",
  email: "member@example.com",
  first_name: "Mem",
  last_name: "Ber",
  is_staff: false,
  is_admin: false,
  is_company: true,
  is_kp_president: false,
  user_confirmed: true,
  email_confirmed: true,
};

const CurrentUserProbe = () => {
  useGetCurrentUser();
  return null;
};

let meRequests = 0;

beforeEach(() => {
  meRequests = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/user/me`, () => {
      meRequests += 1;
      return HttpResponse.json(adminUser);
    }),
    http.get(`${testBackendUrl}/api/users`, () =>
      HttpResponse.json({
        items: [companyUser],
        total: 1,
        page: 1,
        page_size: 25,
      }),
    ),
  );
});

describe("impersonation cache reset", () => {
  it("drops other cached identities when impersonation starts", async () => {
    const queryClient = createCachingQueryClient();
    queryClient.setQueryData(getGetAllStaffQueryKey(), [companyUser]);

    const { user } = renderWithProviders(
      <UserProvider user={adminUser} isLoading={false}>
        <CurrentUserProbe />
        <UserManagement />
      </UserProvider>,
      { queryClient },
    );

    await waitFor(() => {
      expect(meRequests).toBe(1);
    });

    await user.click(
      await screen.findByRole("button", {
        name: "user_management.impersonate",
      }),
    );

    await waitFor(() => {
      expect(meRequests).toBe(2);
    });
    expect(queryClient.getQueryData(getGetAllStaffQueryKey())).toBeUndefined();
  });

  it("drops other cached identities when impersonation stops", async () => {
    setImpersonation(companyUser.id, "Mem Ber");
    const queryClient = createCachingQueryClient();
    queryClient.setQueryData(getGetAllStaffQueryKey(), [companyUser]);

    const { user } = renderWithProviders(
      <UserProvider user={adminUser} isLoading={false}>
        <CurrentUserProbe />
        <RootLayout navbarHidden={false} />
      </UserProvider>,
      { queryClient },
    );

    await waitFor(() => {
      expect(meRequests).toBe(1);
    });

    await user.click(
      screen.getByRole("button", { name: "impersonation.stop" }),
    );

    await waitFor(() => {
      expect(meRequests).toBe(2);
    });
    expect(queryClient.getQueryData(getGetAllStaffQueryKey())).toBeUndefined();
  });
});
