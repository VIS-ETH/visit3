import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpCompanyView from "../../pages/KpCompanyView";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId, testOpenEvent } from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
      HttpResponse.json(testOpenEvent),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/my-booking`, () =>
      HttpResponse.json(
        { statusCode: 500, code: "error.internal", message: "boom" },
        { status: 500 },
      ),
    ),
  );
});

describe("the company event page", () => {
  it("shows an error instead of a new booking when the own booking fails to load", async () => {
    renderWithProviders(
      <Routes>
        <Route path="/kp/:id" element={<KpCompanyView />} />
      </Routes>,
      { route: `/kp/${testEventId}` },
    );

    expect(
      await screen.findByText("error.load_failed", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("kp.company_view.start_booking"),
    ).not.toBeInTheDocument();
  });
});
