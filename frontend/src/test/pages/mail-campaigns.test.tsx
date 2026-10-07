import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import i18n from "i18next";
import enAdmin from "../../../public/locales/en/admin.json";
import MailCampaigns from "../../pages/MailCampaigns";
import type {
  MailCampaignAudienceRequest,
  MailCampaignResponse,
  MailCampaignSummaryResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  testCampaignAudience,
  testCampaignCompanies,
  testCampaignEvent,
  testCampaignPreview,
  testCampaignZone,
  testDraftCampaign,
  testFailedCampaign,
} from "../fixtures/mail-campaign";

const api = (path: string) => `${testBackendUrl}/api${path}`;
const TIMEOUT = { timeout: 5000 };

let campaigns: MailCampaignResponse[] = [];
let audienceRequests: MailCampaignAudienceRequest[] = [];
let calls: { method: string; path: string; body: unknown }[] = [];

const summary = ({
  id,
  name,
  event_id,
  event_name,
  status,
  scheduled_at,
  started_at,
  finished_at,
  created_at,
  updated_at,
  counts,
}: MailCampaignResponse): MailCampaignSummaryResponse => ({
  id,
  name,
  event_id,
  event_name,
  status,
  scheduled_at,
  started_at,
  finished_at,
  created_at,
  updated_at,
  counts,
});

const record = async (request: Request, path: string) => {
  const text = await request.text();
  calls.push({
    method: request.method,
    path,
    body: text ? (JSON.parse(text) as unknown) : null,
  });
};

beforeAll(() => {
  i18n.addResourceBundle("en", "common", {
    mail_campaigns: enAdmin.mail_campaigns,
  });
});

afterAll(() => {
  i18n.removeResourceBundle("en", "common");
  i18n.addResourceBundle("en", "common", {});
});

beforeEach(() => {
  campaigns = [];
  audienceRequests = [];
  calls = [];
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(api("/csrftoken"), () => HttpResponse.json({ token: "csrf-1" })),
    http.get(api("/kp/list"), () => HttpResponse.json([testCampaignEvent])),
    http.get(api("/kp/events/:eventId/booth-zones"), () =>
      HttpResponse.json([testCampaignZone]),
    ),
    http.get(api("/mail-campaigns"), () =>
      HttpResponse.json(campaigns.map(summary)),
    ),
    http.get(api("/mail-campaigns/variables"), () =>
      HttpResponse.json(["company_name", "login_url", "name"]),
    ),
    http.get(api("/mail-campaigns/companies"), () =>
      HttpResponse.json(testCampaignCompanies),
    ),
    http.post(api("/mail-campaigns/audience"), async ({ request }) => {
      const body = (await request.json()) as MailCampaignAudienceRequest;
      audienceRequests.push(body);
      const segments = body.audience.segments ?? [];
      return HttpResponse.json(
        segments.includes("CONFIRMED")
          ? { ...testCampaignAudience, recipient_count: 7 }
          : testCampaignAudience,
      );
    }),
    http.post(api("/mail-campaigns/render"), () =>
      HttpResponse.json(testCampaignPreview),
    ),
    http.get(api("/mail-campaigns/:id"), ({ params }) =>
      HttpResponse.json(campaigns.find((item) => item.id === params.id)),
    ),
    http.post(api("/mail-campaigns"), async ({ request }) => {
      await record(request, "/mail-campaigns");
      const created = { ...testDraftCampaign, id: "campaign-new" };
      campaigns = [created, ...campaigns];
      return HttpResponse.json(created);
    }),
    http.put(api("/mail-campaigns/:id"), async ({ request, params }) => {
      await record(request, `/mail-campaigns/${String(params.id)}`);
      return HttpResponse.json(campaigns.find((item) => item.id === params.id));
    }),
    http.post(
      api("/mail-campaigns/:id/:action"),
      async ({ request, params }) => {
        await record(
          request,
          `/mail-campaigns/${String(params.id)}/${String(params.action)}`,
        );
        const current = campaigns.find((item) => item.id === params.id);
        const status =
          params.action === "schedule"
            ? "SCHEDULED"
            : params.action === "send" || params.action === "retry"
              ? "SENDING"
              : "DRAFT";
        const updated = {
          ...(current ?? testDraftCampaign),
          status,
          updated_at: "2030-05-04T08:00:00Z",
          scheduled_at:
            params.action === "schedule" ? "2030-07-01T07:00:00Z" : null,
        } as MailCampaignResponse;
        campaigns = campaigns.map((item) =>
          item.id === updated.id ? updated : item,
        );
        return HttpResponse.json(updated);
      },
    ),
  );
});

const renderPage = () => renderWithProviders(<MailCampaigns />);

const fillContent = async (user: ReturnType<typeof renderPage>["user"]) => {
  await user.type(
    await screen.findByLabelText("Internal name", {}, TIMEOUT),
    "Reminder",
  );
  await user.type(
    screen.getByLabelText("mail_templates.subject"),
    "Erinnerung",
  );
  await user.type(screen.getByLabelText("mail_templates.body"), "Hallo");
};

const multiSelect = (label: string) => {
  const input = screen
    .getAllByLabelText(label)
    .find(
      (element) =>
        element instanceof HTMLInputElement && element.type !== "hidden",
    );
  if (!input) throw new Error(`no input labelled ${label}`);
  return input;
};

const lastAudience = () => audienceRequests[audienceRequests.length - 1];

describe("the mail campaigns page", () => {
  it("builds the audience and shows the live recipient count", async () => {
    const { user } = renderPage();

    expect(
      await screen.findByText("2 to send, 1 skipped", {}, TIMEOUT),
    ).toBeInTheDocument();
    expect(lastAudience().audience.segments).toEqual(["NOT_REGISTERED"]);
    const recipients = screen.getByRole("table");
    expect(
      within(recipients).getByText("ada@acme.example"),
    ).toBeInTheDocument();
    expect(within(recipients).getByText("General email")).toBeInTheDocument();
    expect(
      within(recipients).getByText("No contact person or general email"),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("checkbox", { name: "Confirmed" }));

    expect(
      await screen.findByText("7 to send, 1 skipped", {}, TIMEOUT),
    ).toBeInTheDocument();
    expect(lastAudience().audience.segments).toEqual([
      "NOT_REGISTERED",
      "CONFIRMED",
    ]);

    await user.click(multiSelect("Booth zones"));
    await user.click(await screen.findByRole("option", { name: "Main hall" }));
    await user.click(multiSelect("Always include"));
    await user.click(await screen.findByRole("option", { name: "Acme AG" }));

    await waitFor(() => {
      expect(lastAudience().audience).toMatchObject({
        booth_zone_ids: [testCampaignZone.id],
        include_company_ids: ["company-acme"],
        exclude_company_ids: [],
      });
    }, TIMEOUT);

    await user.click(multiSelect("Never include"));
    const options = await screen.findAllByRole("option");
    expect(options.map((option) => option.textContent)).not.toContain(
      "Acme AG",
    );
  });

  it("asks for confirmation with the recipient count before sending", async () => {
    const { user } = renderPage();
    await fillContent(user);

    await user.click(screen.getByRole("button", { name: "Send now" }));

    const dialog = await screen.findByRole("dialog", {}, TIMEOUT);
    expect(
      await within(dialog).findByText(
        "The mail goes out now to 2 companies.",
        {},
        TIMEOUT,
      ),
    ).toBeInTheDocument();
    expect(calls).toEqual([]);

    await user.click(within(dialog).getByRole("button", { name: "Send now" }));

    await waitFor(() => {
      expect(calls.map((call) => `${call.method} ${call.path}`)).toEqual([
        "POST /mail-campaigns",
        "POST /mail-campaigns/campaign-new/send",
      ]);
    }, TIMEOUT);
    expect(calls[0].body).toMatchObject({
      name: "Reminder",
      event_id: testCampaignEvent.id,
      subject_de: "Erinnerung",
      body_de: "Hallo",
      subject_en: "",
      body_en: "",
      audience: { segments: ["NOT_REGISTERED"] },
    });
  });

  it("does not send when the confirmation is cancelled", async () => {
    const { user } = renderPage();
    await fillContent(user);

    await user.click(screen.getByRole("button", { name: "Send now" }));
    const dialog = await screen.findByRole("dialog", {}, TIMEOUT);
    await within(dialog).findByText(
      "The mail goes out now to 2 companies.",
      {},
      TIMEOUT,
    );
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    expect(calls).toEqual([]);
  });

  it("does not open the confirmation for an incomplete mail", async () => {
    const { user } = renderPage();
    await screen.findByLabelText("Internal name", {}, TIMEOUT);

    await user.click(screen.getByRole("button", { name: "Send now" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(calls).toEqual([]);
  });

  it("schedules a draft at the chosen Zurich time", async () => {
    campaigns = [testDraftCampaign];
    const { user } = renderPage();

    await screen.findByDisplayValue(testDraftCampaign.name, {}, TIMEOUT);
    await user.click(screen.getByRole("button", { name: "Schedule" }));
    const dialog = await screen.findByRole("dialog", {}, TIMEOUT);
    const input = within(dialog).getByLabelText("Date and time (Zurich time)");

    fireEvent.change(input, { target: { value: "2020-01-01T09:00" } });
    expect(
      within(dialog).getByText("Pick a time in the future."),
    ).toBeVisible();
    expect(
      within(dialog).getByRole("button", { name: "Schedule" }),
    ).toBeDisabled();

    fireEvent.change(input, { target: { value: "2030-07-01T09:00" } });
    await user.click(within(dialog).getByRole("button", { name: "Schedule" }));

    await waitFor(() => {
      expect(calls.map((call) => `${call.method} ${call.path}`)).toEqual([
        "PUT /mail-campaigns/campaign-1",
        "POST /mail-campaigns/campaign-1/schedule",
      ]);
    }, TIMEOUT);
    expect(calls[1].body).toEqual({ scheduled_at: "2030-07-01T09:00" });
    expect(
      await screen.findByRole("button", { name: "Cancel schedule" }, TIMEOUT),
    ).toBeInTheDocument();
  });

  it("shows the per-recipient log and retries failed mails", async () => {
    campaigns = [testFailedCampaign];
    const { user } = renderPage();

    const row = await screen.findByRole("row", { name: /Beta GmbH/ }, TIMEOUT);
    expect(within(row).getByText("info@beta.example")).toBeInTheDocument();
    expect(within(row).getByText("Failed")).toBeInTheDocument();
    expect(
      within(row).getByText("Rejected by the mail service"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("mail-campaign-sent")).toHaveTextContent("1");
    expect(screen.getByTestId("mail-campaign-failed")).toHaveTextContent("1");

    await user.click(screen.getByRole("radio", { name: "Failed" }));
    expect(
      screen.queryByRole("row", { name: /Acme AG/ }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry failed (1)" }));

    await waitFor(() => {
      expect(calls.map((call) => `${call.method} ${call.path}`)).toEqual([
        "POST /mail-campaigns/campaign-2/retry",
      ]);
    }, TIMEOUT);
  });
});
