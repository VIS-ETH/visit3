import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import Profile from "../../pages/Profile";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";

const storedProfile = {
  id: "user-1",
  email: "member@example.com",
  first_name: "Mem",
  last_name: "Ber",
  phone_number: "+41791234567",
  is_staff: false,
  is_admin: false,
  is_company: true,
  user_confirmed: true,
  email_confirmed: true,
  company_id: "company-1",
};

let updateBodies: unknown[] = [];

beforeEach(() => {
  updateBodies = [];
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/user/profile`, () =>
      HttpResponse.json(storedProfile),
    ),
    http.patch(`${testBackendUrl}/api/user/me`, async ({ request }) => {
      updateBodies.push(await request.json());
      return HttpResponse.json(storedProfile);
    }),
  );
});

describe("Profile update payload", () => {
  it("sends only the fields the user changed", async () => {
    const { user } = renderWithProviders(<Profile />);

    await user.click(
      await screen.findByRole("button", { name: "profile.edit.button" }),
    );

    const firstName = await screen.findByLabelText("profile.edit.first_name");
    await user.clear(firstName);
    await user.type(firstName, "Memo");
    await user.click(screen.getByRole("button", { name: "profile.edit.save" }));

    await waitFor(() => {
      expect(updateBodies).toHaveLength(1);
    });
    expect(updateBodies[0]).toEqual({ first_name: "Memo" });
  });
});
