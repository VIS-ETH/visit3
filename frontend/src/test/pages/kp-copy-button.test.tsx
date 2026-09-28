import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes, useParams } from "react-router";
import KpDashboard from "../../pages/KpDashboard";
import type { KpResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEvent } from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const olderEvent: KpResponse = {
  ...testEvent,
  id: "11111111-1111-1111-1111-111111111111",
  name: "KP 2025",
  event_date: "2025-10-01",
};

const latestEvent: KpResponse = {
  ...testEvent,
  id: "22222222-2222-2222-2222-222222222222",
  name: "KP 2026",
  event_date: "2026-10-01",
};

const clonedEventId = "33333333-3333-3333-3333-333333333333";

let cloneRequests: { sourceId: string; name: unknown }[] = [];

const EventPage = () => {
  const { id } = useParams<{ id: string }>();
  return <p data-testid="event-page">{id}</p>;
};

const renderDashboard = () =>
  renderWithProviders(
    <Routes>
      <Route path="/kp" element={<KpDashboard />} />
      <Route path="/kp/:id" element={<EventPage />} />
    </Routes>,
    { route: "/kp" },
  );

const openCopyModal = async (user: UserEvent) => {
  await user.click(
    await screen.findByRole(
      "button",
      { name: "kp.dashboard.copy_button" },
      SLOW_WAIT,
    ),
  );
  return screen.findByRole("dialog", undefined, SLOW_WAIT);
};

const fillCloneForm = async (user: UserEvent, dialog: HTMLElement) => {
  const fields: [string, string][] = [
    ["kp.dashboard.name", "KP 2027"],
    ["kp.dashboard.registration_open", "01.09.2027"],
    ["kp.dashboard.registration_end", "30.09.2027"],
    ["kp.dashboard.finalization_deadline", "05.10.2027"],
    ["kp.dashboard.nametags_deadline", "06.10.2027"],
    ["kp.dashboard.event_date", "20.10.2027"],
  ];
  for (const [label, value] of fields) {
    await user.type(within(dialog).getByLabelText(label), value);
  }
};

beforeEach(() => {
  cloneRequests = [];
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/list`, () =>
      HttpResponse.json([olderEvent, latestEvent]),
    ),
    http.post(
      `${testBackendUrl}/api/kp/events/:eventId/clone`,
      async ({ params, request }) => {
        const body = (await request.json()) as { name: unknown };
        cloneRequests.push({
          sourceId: String(params.eventId),
          name: body.name,
        });
        return HttpResponse.json({
          ...latestEvent,
          id: clonedEventId,
          name: body.name,
        });
      },
    ),
  );
});

describe("the copy Kontaktparty button", () => {
  it("opens the clone form with the latest event as source", async () => {
    const { user } = renderDashboard();

    const dialog = await openCopyModal(user);

    expect(
      within(dialog).getByRole("combobox", {
        name: "kp.dashboard.copy_source",
      }),
    ).toHaveValue(latestEvent.name);
    expect(
      within(dialog).getByRole("button", { name: "kp.manage.clone_submit" }),
    ).toBeInTheDocument();
  });

  it("clones the latest event and opens the new one", async () => {
    const { user } = renderDashboard();
    const dialog = await openCopyModal(user);

    await fillCloneForm(user, dialog);
    await user.click(
      within(dialog).getByRole("button", { name: "kp.manage.clone_submit" }),
    );

    await waitFor(() =>
      expect(cloneRequests).toEqual([
        { sourceId: latestEvent.id, name: "KP 2027" },
      ]),
    );
    expect(
      await screen.findByTestId("event-page", undefined, SLOW_WAIT),
    ).toHaveTextContent(clonedEventId);
  });

  it("clones the chosen older event", async () => {
    const { user } = renderDashboard();
    const dialog = await openCopyModal(user);

    await user.click(
      within(dialog).getByRole("combobox", {
        name: "kp.dashboard.copy_source",
      }),
    );
    await user.click(
      await screen.findByRole("option", { name: olderEvent.name }),
    );
    await fillCloneForm(user, dialog);
    await user.click(
      within(dialog).getByRole("button", { name: "kp.manage.clone_submit" }),
    );

    await waitFor(() =>
      expect(cloneRequests).toEqual([
        { sourceId: olderEvent.id, name: "KP 2027" },
      ]),
    );
  });
});
