import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import KpJoin from "../../pages/KpJoin";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEvent } from "../fixtures/kp-booking";
import { SLOW_WAIT } from "../timeouts";

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/kp/latest`, () =>
      HttpResponse.json({ ...testEvent, name: "KP 2026" }),
    ),
  );
});

describe("the Kontaktparty join page", () => {
  it("separates each label from its value", async () => {
    const { container } = renderWithProviders(<KpJoin />);

    await screen.findByText("KP 2026", { exact: false }, SLOW_WAIT);
    expect(container.textContent).toContain("kp.join.name: KP 2026");
  });
});
