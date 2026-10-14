import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import Profile from "../../pages/Profile";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { notificationsShow } from "../notifications";
import { renderWithProviders } from "../render";

const NEW_EMAIL = "moved@example.com";

const storedProfile = {
  id: "user-1",
  email: "member@example.com",
  first_name: "Mem",
  last_name: "Ber",
  phone_number: "+41791234567",
  user_confirmed: true,
  email_confirmed: true,
  pending_email: null as string | null,
};

let profile = storedProfile;
let changeBodies: unknown[] = [];

beforeEach(() => {
  profile = { ...storedProfile };
  changeBodies = [];
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/user/profile`, () =>
      HttpResponse.json(profile),
    ),
    http.post(`${testBackendUrl}/api/user/me/email`, async ({ request }) => {
      changeBodies.push(await request.json());
      profile = { ...profile, pending_email: NEW_EMAIL };
      return HttpResponse.json(profile);
    }),
  );
});

const openDialog = async () => {
  const { user } = renderWithProviders(<Profile />);
  await user.click(
    await screen.findByRole("button", { name: "profile.email_change.button" }),
  );
  const input = await screen.findByLabelText("profile.email_change.email");
  return { user, input };
};

describe("Profile email change", () => {
  it("sends the new address and shows it as pending", async () => {
    const { user, input } = await openDialog();

    await user.type(input, NEW_EMAIL);
    await user.click(
      screen.getByRole("button", { name: "profile.email_change.submit" }),
    );

    await waitFor(() => {
      expect(changeBodies).toEqual([{ email: NEW_EMAIL }]);
    });
    expect(notificationsShow).toHaveBeenCalledWith(
      expect.objectContaining({ message: "profile.email_change.sent_message" }),
    );
    expect(
      await screen.findByText("profile.email_change.pending"),
    ).toBeInTheDocument();
  });

  it("shows a change that still waits for its confirmation", async () => {
    profile = { ...storedProfile, pending_email: NEW_EMAIL };

    renderWithProviders(<Profile />);

    expect(
      await screen.findByText("profile.email_change.pending"),
    ).toBeInTheDocument();
  });

  it("rejects an invalid address without sending it", async () => {
    const { user, input } = await openDialog();

    await user.type(input, "not-an-address");
    await user.click(
      screen.getByRole("button", { name: "profile.email_change.submit" }),
    );

    expect(
      await screen.findByText("validation.invalid_email"),
    ).toBeInTheDocument();
    expect(changeBodies).toEqual([]);
  });

  it("does not offer to send the current address", async () => {
    const { user, input } = await openDialog();

    await user.type(input, "Member@Example.com");

    expect(
      screen.getByRole("button", { name: "profile.email_change.submit" }),
    ).toBeDisabled();
  });
});
