import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import DetailsTab from "../../components/DetailsTab";
import { UserProvider } from "../../context/UserContext";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEvent, testEventId } from "../fixtures/kp-booking";

const otherEventId = "99999999-9999-9999-9999-999999999999";

const staffUser: UserResponse = {
  id: "staff-1",
  email: "staff@example.com",
  is_staff: true,
  is_admin: false,
  is_company: false,
  is_kp_president: false,
  user_confirmed: true,
  email_confirmed: true,
};

const renderDetailsTab = (eventId: string) => (
  <UserProvider user={staffUser} isLoading={false}>
    <DetailsTab eventId={eventId} />
  </UserProvider>
);

const otherEvent = {
  ...testEvent,
  id: otherEventId,
  name: "Second Kontaktparty",
  event_date: "2027-05-02T00:00:00Z",
};

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId`, ({ params }) =>
      HttpResponse.json(
        params.eventId === otherEventId ? otherEvent : testEvent,
      ),
    ),
  );
});

describe("DetailsTab", () => {
  it("fills the form once the event has loaded", async () => {
    renderWithProviders(renderDetailsTab(testEventId));

    await waitFor(
      () => {
        expect(screen.getByLabelText("kp.dashboard.name")).toHaveValue(
          testEvent.name,
        );
      },
      { timeout: 5000 },
    );
    expect(screen.getByLabelText("kp.dashboard.event_date")).toHaveValue(
      "01.04.2026",
    );
  });

  it("re-initialises when another event is selected", async () => {
    const { rerender } = renderWithProviders(renderDetailsTab(testEventId));

    await waitFor(
      () => {
        expect(screen.getByLabelText("kp.dashboard.name")).toHaveValue(
          testEvent.name,
        );
      },
      { timeout: 5000 },
    );

    rerender(renderDetailsTab(otherEventId));

    await waitFor(
      () => {
        expect(screen.getByLabelText("kp.dashboard.name")).toHaveValue(
          otherEvent.name,
        );
      },
      { timeout: 5000 },
    );
    expect(screen.getByLabelText("kp.dashboard.event_date")).toHaveValue(
      "02.05.2027",
    );
  });
});
