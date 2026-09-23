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

const presidentUser: UserResponse = {
  id: "president-1",
  email: "president@example.com",
  is_staff: true,
  is_admin: false,
  is_company: false,
  is_kp_president: true,
  user_confirmed: true,
  email_confirmed: true,
};

const eventSettings = {
  ...testEvent,
  terms_url: "https://example.com/terms",
  notification_email: "kp@example.com",
};

let updateBodies: unknown[] = [];

const renderDetailsTab = () =>
  renderWithProviders(
    <UserProvider user={presidentUser} isLoading={false}>
      <DetailsTab eventId={testEventId} />
    </UserProvider>,
  );

const waitForLoadedForm = async () => {
  await waitFor(
    () => {
      expect(
        screen.getByLabelText("event_settings.notification_email"),
      ).toHaveValue(eventSettings.notification_email);
    },
    { timeout: 5000 },
  );
};

beforeEach(() => {
  updateBodies = [];
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/settings`, () =>
      HttpResponse.json(eventSettings),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
      HttpResponse.json(eventSettings),
    ),
    http.patch(
      `${testBackendUrl}/api/kp/events/:eventId`,
      async ({ request }) => {
        updateBodies.push(await request.json());
        return HttpResponse.json(eventSettings);
      },
    ),
  );
});

describe("the event settings section", () => {
  it("shows the stored settings once the event has loaded", async () => {
    renderDetailsTab();

    await waitForLoadedForm();
    expect(screen.getByLabelText("event_settings.terms_url")).toHaveValue(
      eventSettings.terms_url,
    );
    expect(screen.getByLabelText("event_settings.reminder_days")).toHaveValue(
      String(eventSettings.finalization_reminder_days),
    );
  });

  it("rejects a terms link that is not an http url", async () => {
    const { user } = renderDetailsTab();

    await waitForLoadedForm();
    const termsUrl = screen.getByLabelText("event_settings.terms_url");
    await user.clear(termsUrl);
    await user.type(termsUrl, "example.com/terms");

    expect(
      await screen.findByText("validation.invalid_url", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  it("rejects a notification address that is not an email", async () => {
    const { user } = renderDetailsTab();

    await waitForLoadedForm();
    const notificationEmail = screen.getByLabelText(
      "event_settings.notification_email",
    );
    await user.clear(notificationEmail);
    await user.type(notificationEmail, "not-an-email");

    expect(
      await screen.findByText(
        "validation.invalid_email",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
  });

  it("sends the settings fields with the update", async () => {
    const { user } = renderDetailsTab();

    await waitForLoadedForm();

    const reminderDays = screen.getByLabelText("event_settings.reminder_days");
    await user.clear(reminderDays);
    await user.type(reminderDays, "7");

    const notificationEmail = screen.getByLabelText(
      "event_settings.notification_email",
    );
    await user.clear(notificationEmail);

    await user.click(screen.getByRole("button", { name: "kp.manage.save" }));

    await waitFor(() => {
      expect(updateBodies).toHaveLength(1);
    });
    expect(updateBodies[0]).toMatchObject({
      vat_rate_percent: 8.1,
      terms_url: "https://example.com/terms",
      notification_email: null,
      finalization_reminder_days: 7,
    });
  });
});
