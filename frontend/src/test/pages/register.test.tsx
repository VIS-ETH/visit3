import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import Register from "../../pages/Register";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { renderWithProviders } from "../render";

let registerBodies: unknown[] = [];

beforeEach(() => {
  registerBodies = [];
  server.use(
    http.post(`${testBackendUrl}/api/auth/register`, async ({ request }) => {
      registerBodies.push(await request.json());
      await delay(300);
      return new HttpResponse(null, { status: 200 });
    }),
  );
});

describe("Register", () => {
  it("sends one trimmed registration when Enter is pressed twice", async () => {
    const { user } = renderWithProviders(<Register />);

    await user.type(screen.getByLabelText(/register.first_name/), "Ada");
    await user.type(screen.getByLabelText(/register.last_name/), "Lovelace");
    await user.type(screen.getByLabelText(/email.title/), " ada@example.com ");
    await user.type(
      screen.getByLabelText(/^register.password.title/),
      "password123",
    );
    await user.type(
      screen.getByLabelText(/register.password.confirm/),
      "password123{Enter}{Enter}",
    );

    expect(
      await screen.findByText("register.success.title", {}, { timeout: 2000 }),
    ).toBeInTheDocument();
    expect(registerBodies).toHaveLength(1);
    expect(registerBodies[0]).toMatchObject({ email: "ada@example.com" });
  });
});
