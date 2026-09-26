import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
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
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
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
      missing_items: ["billing_address", "company_description"],
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
