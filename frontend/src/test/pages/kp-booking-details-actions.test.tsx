import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingDetails from "../../pages/KpBookingDetails";
import {
  KpBookingStatus,
  type StaffBookingResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { notificationsShow } from "../notifications";
import { testEventId } from "../fixtures/kp-booking";
import { emptyVenueHandler } from "../fixtures/venue";
import { acmeBooking, acmeBookingId } from "../fixtures/staff-bookings";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const detailsPath = "/kp/:id/bookings/:bookingId";
const detailsRoute = `/kp/${testEventId}/bookings/${acmeBookingId}`;

const formatted = (value: string) =>
  new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));

const detailRequests = { count: 0 };

const serveBooking = (booking: StaffBookingResponse) => {
  server.use(
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/bookings/:bookingId`,
      () => {
        detailRequests.count += 1;
        return HttpResponse.json(booking);
      },
    ),
  );
};

const renderDetails = () =>
  renderWithProviders(
    <Routes>
      <Route path={detailsPath} element={<KpBookingDetails />} />
      <Route path="/kp/:id" element={<div data-testid="bookings-list" />} />
    </Routes>,
    { route: detailsRoute },
  );

beforeEach(() => {
  detailRequests.count = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    emptyVenueHandler,
    http.get(
      `${testBackendUrl}/api/kp/staff/events/:eventId/bookings/:bookingId/requirement-files`,
      () => HttpResponse.json({ files: {} }),
    ),
    http.get(
      `${testBackendUrl}/api/kp/staff/bookings/:bookingId/nametags`,
      () => HttpResponse.json([]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/bookings`, () =>
      HttpResponse.json([acmeBooking]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/booth-zones`, () =>
      HttpResponse.json([]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/services`, () =>
      HttpResponse.json([]),
    ),
  );
});

describe("the staff booking details header", () => {
  it("shows how far the booking got and what is still open", async () => {
    serveBooking(acmeBooking);
    renderDetails();

    expect(
      await screen.findByText(
        "kp.manage.booking_timeline_title",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.manage.booking_timeline_registered"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(formatted(acmeBooking.status_changed_at ?? "")),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.manage.booking_timeline_pending"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.manage.booking_completeness_complete"),
    ).toBeInTheDocument();
  });

  it("lists the missing items, the rejection reason and the internal note", async () => {
    serveBooking({
      ...acmeBooking,
      is_complete: false,
      missing_items: [
        "billing_address",
        "company_description",
        "general_email",
      ],
      rejection_reason: "The booth zone does not fit the company size.",
      status: KpBookingStatus.REJECTED,
      status_note: "Called the company on Monday.",
    });
    renderDetails();

    expect(
      await screen.findByText(
        "kp.manage.booking_missing_item_billing_address",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.manage.booking_missing_item_company_description"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.manage.booking_missing_item_general_email"),
    ).toBeInTheDocument();
    const notices = screen.getAllByRole("alert");
    expect(notices[0]).toHaveTextContent(
      "The booth zone does not fit the company size.",
    );
    expect(notices[1]).toHaveTextContent("Called the company on Monday.");
    expect(
      screen.getByText("kp.manage.booking_timeline_rejected"),
    ).toBeInTheDocument();
  });
});

describe("the staff booking details actions", () => {
  it("only enables the transitions the status allows", async () => {
    serveBooking(acmeBooking);
    renderDetails();

    expect(
      await screen.findByRole(
        "button",
        { name: "kp.manage.booking_action_accept" },
        { timeout: 5000 },
      ),
    ).toBeEnabled();
    expect(
      screen.getByRole("button", {
        name: "kp.manage.booking_action_undo_accept",
      }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "kp.manage.booking_action_reject" }),
    ).toBeEnabled();
  });

  it("accepts the booking and reloads it", async () => {
    const accepted: string[] = [];
    serveBooking(acmeBooking);
    server.use(
      http.post(
        `${testBackendUrl}/api/kp/bookings/:bookingId/accept`,
        ({ params }) => {
          accepted.push(String(params.bookingId));
          return HttpResponse.json(acmeBooking);
        },
      ),
    );
    const { user } = renderDetails();

    await user.click(
      await screen.findByRole(
        "button",
        { name: "kp.manage.booking_action_accept" },
        { timeout: 5000 },
      ),
    );
    const requestsBefore = detailRequests.count;
    await user.click(
      await screen.findByRole("button", {
        name: "kp.manage.booking_accept_submit",
      }),
    );

    await waitFor(() => expect(accepted).toEqual([acmeBookingId]));
    await waitFor(() =>
      expect(detailRequests.count).toBeGreaterThan(requestsBefore),
    );
    expect(notificationsShow).toHaveBeenCalledWith({
      color: "green",
      message: "kp.manage.booking_accepted",
    });
  });

  it("undoes the acceptance of a confirmed booking", async () => {
    const undone: string[] = [];
    serveBooking({ ...acmeBooking, status: KpBookingStatus.CONFIRMED });
    server.use(
      http.post(
        `${testBackendUrl}/api/kp/bookings/:bookingId/undo-accept`,
        ({ params }) => {
          undone.push(String(params.bookingId));
          return HttpResponse.json(acmeBooking);
        },
      ),
    );
    const { user } = renderDetails();

    await user.click(
      await screen.findByRole(
        "button",
        { name: "kp.manage.booking_action_undo_accept" },
        { timeout: 5000 },
      ),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "kp.manage.booking_undo_accept_submit",
      }),
    );

    await waitFor(() => expect(undone).toEqual([acmeBookingId]));
  });

  it("sends the typed reason when it rejects", async () => {
    const reasons: string[] = [];
    serveBooking(acmeBooking);
    server.use(
      http.post(
        `${testBackendUrl}/api/kp/bookings/:bookingId/reject`,
        async ({ request }) => {
          const body = (await request.json()) as { reason: string };
          reasons.push(body.reason);
          return HttpResponse.json(acmeBooking);
        },
      ),
    );
    const { user } = renderDetails();

    await user.click(
      await screen.findByRole(
        "button",
        { name: "kp.manage.booking_action_reject" },
        { timeout: 5000 },
      ),
    );
    const submit = await screen.findByRole("button", {
      name: "kp.manage.booking_reject_submit",
    });
    expect(submit).toBeDisabled();

    await user.type(
      screen.getByLabelText("kp.manage.booking_reject_reason"),
      "The requested booth zone is reserved for sponsors.",
    );
    await user.click(submit);

    await waitFor(() =>
      expect(reasons).toEqual([
        "The requested booth zone is reserved for sponsors.",
      ]),
    );
  });

  it("forces the delete of a confirmed booking and goes back to the list", async () => {
    const deletions: (string | null)[] = [];
    serveBooking({ ...acmeBooking, status: KpBookingStatus.CONFIRMED });
    server.use(
      http.delete(
        `${testBackendUrl}/api/kp/bookings/:bookingId`,
        ({ request }) => {
          deletions.push(new URL(request.url).searchParams.get("force"));
          return HttpResponse.json(null);
        },
      ),
    );
    const { user } = renderDetails();

    await user.click(
      await screen.findByRole(
        "button",
        { name: "kp.manage.booking_action_delete" },
        { timeout: 5000 },
      ),
    );
    const submit = await screen.findByRole("button", {
      name: "kp.manage.booking_delete_submit",
    });
    expect(submit).toBeDisabled();

    await user.click(screen.getByLabelText("kp.manage.booking_delete_force"));
    await user.click(submit);

    await waitFor(() => expect(deletions).toEqual(["true"]));
    expect(await screen.findByTestId("bookings-list")).toBeInTheDocument();
  });
});

describe("services added after the confirmation", () => {
  const confirmedWithAddition = (): StaffBookingResponse => ({
    ...acmeBooking,
    status: KpBookingStatus.CONFIRMED,
    added_after_confirmation: [
      {
        booking_service_id: (acmeBooking.services ?? [])[0].id,
        quantity: 1,
      },
    ],
  });

  it("marks the added line and lets staff mark it as seen", async () => {
    let current = confirmedWithAddition();
    const acknowledged: string[] = [];
    server.use(
      http.get(
        `${testBackendUrl}/api/kp/events/:eventId/bookings/:bookingId`,
        () => HttpResponse.json(current),
      ),
      http.post(
        `${testBackendUrl}/api/kp/bookings/:bookingId/acknowledge-additions`,
        ({ params }) => {
          acknowledged.push(String(params.bookingId));
          current = { ...current, added_after_confirmation: [] };
          return HttpResponse.json(current);
        },
      ),
    );
    const { user } = renderDetails();

    expect(
      await screen.findByText(
        "kp.manage.booking_service_added",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", {
        name: "kp.manage.booking_additions_acknowledge",
      }),
    );

    await waitFor(() => expect(acknowledged).toEqual([acmeBookingId]));
    await waitFor(() =>
      expect(
        screen.queryByText("kp.manage.booking_service_added"),
      ).not.toBeInTheDocument(),
    );
    expect(
      screen.queryByRole("button", {
        name: "kp.manage.booking_additions_acknowledge",
      }),
    ).not.toBeInTheDocument();
  });

  it("shows no marker without additions", async () => {
    serveBooking({ ...acmeBooking, status: KpBookingStatus.CONFIRMED });
    renderDetails();

    await screen.findByText(
      "kp.manage.booking_timeline_title",
      {},
      { timeout: 5000 },
    );
    expect(
      screen.queryByText("kp.manage.booking_service_added"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "kp.manage.booking_additions_acknowledge",
      }),
    ).not.toBeInTheDocument();
  });
});

describe("the staff booking details while it reloads", () => {
  it("keeps confirm disabled until the accepted booking reloaded", async () => {
    let accepts = 0;
    server.use(
      http.get(
        `${testBackendUrl}/api/kp/events/:eventId/bookings/:bookingId`,
        async () => {
          detailRequests.count += 1;
          if (detailRequests.count > 1) await delay(1500);
          return HttpResponse.json(acmeBooking);
        },
      ),
      http.post(`${testBackendUrl}/api/kp/bookings/:bookingId/accept`, () => {
        accepts += 1;
        return HttpResponse.json(acmeBooking);
      }),
    );
    const { user } = renderDetails();
    await user.click(
      await screen.findByRole(
        "button",
        { name: "kp.manage.booking_action_accept" },
        SLOW_WAIT,
      ),
    );
    const submit = await screen.findByRole("button", {
      name: "kp.manage.booking_accept_submit",
    });
    await user.click(submit);
    await waitFor(() => expect(detailRequests.count).toBe(2));

    expect(submit).toBeDisabled();
    await waitFor(
      () =>
        expect(
          screen.queryByRole("button", {
            name: "kp.manage.booking_accept_submit",
          }),
        ).toBeNull(),
      SLOW_WAIT,
    );
    expect(accepts).toBe(1);
  });
});

describe("requirement downloads of a staff booking", () => {
  const rejections: unknown[] = [];
  const onRejection = (reason: unknown) => {
    rejections.push(reason);
  };

  beforeEach(() => {
    rejections.length = 0;
    process.on("unhandledRejection", onRejection);
  });

  afterEach(() => {
    process.off("unhandledRejection", onRejection);
  });

  it("handles a failed download without an unhandled rejection", async () => {
    const service = {
      id: "svc-1",
      event_id: testEventId,
      name: "Booth package",
      description: "",
      confirmation_description: null,
      order: 1,
      price: 100,
      max_quantity_per_booking: 1,
      max_total_quantity: 0,
      category: "SERVICE",
      unit_label: null,
      is_active: true,
      requirements: [
        {
          id: "req-1",
          service_id: "svc-1",
          type: "pdf",
          name: "Brochure",
          description: "A brochure for the booth",
          order: 1,
        },
      ],
    };
    serveBooking({
      ...acmeBooking,
      services: [
        {
          ...(acmeBooking.services?.[0] ?? {}),
          id: "bs-1",
          quantity: 1,
          service,
        },
      ],
    } as StaffBookingResponse);
    server.use(
      http.get(
        `${testBackendUrl}/api/kp/staff/events/:eventId/bookings/:bookingId/requirement-files`,
        () =>
          HttpResponse.json({
            files: {
              "req-1": {
                id: "f-1",
                booking_service_id: "bs-1",
                requirement_id: "req-1",
                stored_file: {
                  id: "s-1",
                  original_filename: "brochure.pdf",
                  mime_type: "application/pdf",
                  size_bytes: 8,
                  sha256: "x",
                },
              },
            },
          }),
      ),
      http.get(`${testBackendUrl}/api/kp/staff/*`, () =>
        HttpResponse.json({ statusCode: 500 }, { status: 500 }),
      ),
    );
    const { user } = renderDetails();
    const download = await screen.findByRole(
      "button",
      { name: "kp.manage.booking_requirement_download" },
      SLOW_WAIT,
    );
    await user.click(download);

    await waitFor(() => expect(download).toBeEnabled());
    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(rejections).toHaveLength(0);
  });
});
