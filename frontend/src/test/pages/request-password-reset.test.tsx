import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import RequestPasswordReset from "../../pages/RequestPasswordReset";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { renderWithProviders } from "../render";

let resetBodies: unknown[] = [];

beforeEach(() => {
  resetBodies = [];
  server.use(
    http.post(
      `${testBackendUrl}/api/auth/reset-password`,
      async ({ request }) => {
        resetBodies.push(await request.json());
        return new HttpResponse(null, { status: 200 });
      },
    ),
  );
});

const submit = () =>
  screen.getByRole("button", { name: "password_reset_request.submit" });

describe("RequestPasswordReset", () => {
  it("trims whitespace an autocomplete adds to the email", async () => {
    const { user } = renderWithProviders(<RequestPasswordReset />);

    await user.type(screen.getByLabelText("email.title"), " user@example.com");
    await user.click(submit());

    await waitFor(() => expect(resetBodies).toHaveLength(1));
    expect(resetBodies[0]).toEqual({ email: "user@example.com" });
  });

  it("sends again once a mistyped address is corrected", async () => {
    const { user } = renderWithProviders(<RequestPasswordReset />);
    const email = screen.getByLabelText("email.title");

    await user.type(email, "user@exmaple.com");
    await user.click(submit());
    await waitFor(() => expect(submit()).toBeDisabled());

    await user.clear(email);
    await user.type(email, "user@example.com");
    await user.click(submit());

    await waitFor(() => expect(resetBodies).toHaveLength(2));
    expect(resetBodies[1]).toEqual({ email: "user@example.com" });
  });
});
