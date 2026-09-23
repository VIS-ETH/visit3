import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import BookingsTab from "../../components/BookingsTab";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { notificationsShow } from "../notifications";
import { testEventId } from "../fixtures/kp-booking";
import {
  acmeBooking,
  acmeBookingId,
  staffBookings,
  zetaBookingId,
} from "../fixtures/staff-bookings";

const listRequests = { count: 0 };

const openRowMenu = async (
  user: ReturnType<typeof renderWithProviders>["user"],
  index: number,
) => {
  await user.click(
    screen.getAllByLabelText("kp.manage.booking_actions")[index],
  );
};

beforeEach(() => {
  listRequests.count = 0;
  localStorage.setItem("token", createToken(3600));
  window.URL.createObjectURL = vi.fn(() => "blob:bookings");
  window.URL.revokeObjectURL = vi.fn();
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/bookings`, () => {
      listRequests.count += 1;
      return HttpResponse.json(staffBookings);
    }),
  );
});

describe("the staff booking row actions", () => {
  it("only offers the transitions the status allows", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });

    await openRowMenu(user, 0);
    expect(
      await screen.findByRole("menuitem", {
        name: "kp.manage.booking_action_accept",
      }),
    ).toBeEnabled();
    expect(
      screen.getByRole("menuitem", { name: "kp.manage.booking_action_reject" }),
    ).toBeEnabled();
    expect(
      screen.getByRole("menuitem", {
        name: "kp.manage.booking_action_undo_accept",
      }),
    ).toBeDisabled();
    expect(
      screen.getByRole("menuitem", { name: "kp.manage.booking_action_delete" }),
    ).toBeEnabled();
  });

  it("offers undo accept instead of accept on a confirmed booking", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });

    await openRowMenu(user, 2);
    expect(
      await screen.findByRole("menuitem", {
        name: "kp.manage.booking_action_undo_accept",
      }),
    ).toBeEnabled();
    expect(
      screen.getByRole("menuitem", { name: "kp.manage.booking_action_accept" }),
    ).toBeDisabled();
    expect(
      screen.getByRole("menuitem", { name: "kp.manage.booking_action_reject" }),
    ).toBeDisabled();
  });

  it("blocks every transition on a registered booking except reject", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });

    await openRowMenu(user, 1);
    expect(
      await screen.findByRole("menuitem", {
        name: "kp.manage.booking_action_reject",
      }),
    ).toBeEnabled();
    expect(
      screen.getByRole("menuitem", { name: "kp.manage.booking_action_accept" }),
    ).toBeDisabled();
    expect(
      screen.getByRole("menuitem", {
        name: "kp.manage.booking_action_undo_accept",
      }),
    ).toBeDisabled();
  });

  it("accepts a finalized booking and reloads the list", async () => {
    const accepted: string[] = [];
    server.use(
      http.post(
        `${testBackendUrl}/api/kp/bookings/:bookingId/accept`,
        ({ params }) => {
          accepted.push(String(params.bookingId));
          return HttpResponse.json(acmeBooking);
        },
      ),
    );
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    const listRequestsBefore = listRequests.count;
    await openRowMenu(user, 0);
    await user.click(
      await screen.findByRole("menuitem", {
        name: "kp.manage.booking_action_accept",
      }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "kp.manage.booking_accept_submit",
      }),
    );

    await waitFor(() => expect(accepted).toEqual([acmeBookingId]));
    await waitFor(() =>
      expect(listRequests.count).toBeGreaterThan(listRequestsBefore),
    );
    expect(notificationsShow).toHaveBeenCalledWith({
      color: "green",
      message: "kp.manage.booking_accepted",
    });
  });

  it("undoes the acceptance of a confirmed booking", async () => {
    const undone: string[] = [];
    server.use(
      http.post(
        `${testBackendUrl}/api/kp/bookings/:bookingId/undo-accept`,
        ({ params }) => {
          undone.push(String(params.bookingId));
          return HttpResponse.json(acmeBooking);
        },
      ),
    );
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    await openRowMenu(user, 2);
    await user.click(
      await screen.findByRole("menuitem", {
        name: "kp.manage.booking_action_undo_accept",
      }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "kp.manage.booking_undo_accept_submit",
      }),
    );

    await waitFor(() => expect(undone).toEqual([zetaBookingId]));
  });

  it("requires a long enough reason before it rejects", async () => {
    const rejections: { bookingId: string; reason: string }[] = [];
    server.use(
      http.post(
        `${testBackendUrl}/api/kp/bookings/:bookingId/reject`,
        async ({ params, request }) => {
          const body = (await request.json()) as { reason: string };
          rejections.push({
            bookingId: String(params.bookingId),
            reason: body.reason,
          });
          return HttpResponse.json(acmeBooking);
        },
      ),
    );
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    await openRowMenu(user, 0);
    await user.click(
      await screen.findByRole("menuitem", {
        name: "kp.manage.booking_action_reject",
      }),
    );

    const submit = await screen.findByRole("button", {
      name: "kp.manage.booking_reject_submit",
    });
    expect(submit).toBeDisabled();

    const reason = screen.getByLabelText("kp.manage.booking_reject_reason");
    await user.type(reason, "too short");
    expect(
      screen.getByText("kp.manage.booking_reject_reason_too_short"),
    ).toBeInTheDocument();
    expect(submit).toBeDisabled();

    await user.type(reason, " but now it is long enough");
    expect(submit).toBeEnabled();
    await user.click(submit);

    await waitFor(() =>
      expect(rejections).toEqual([
        {
          bookingId: acmeBookingId,
          reason: "too short but now it is long enough",
        },
      ]),
    );
  });

  it("asks for an extra confirmation before it deletes a confirmed booking", async () => {
    const deletions: { bookingId: string; force: string | null }[] = [];
    server.use(
      http.delete(
        `${testBackendUrl}/api/kp/bookings/:bookingId`,
        ({ params, request }) => {
          deletions.push({
            bookingId: String(params.bookingId),
            force: new URL(request.url).searchParams.get("force"),
          });
          return HttpResponse.json(null);
        },
      ),
    );
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    await openRowMenu(user, 2);
    await user.click(
      await screen.findByRole("menuitem", {
        name: "kp.manage.booking_action_delete",
      }),
    );

    const submit = await screen.findByRole("button", {
      name: "kp.manage.booking_delete_submit",
    });
    expect(submit).toBeDisabled();

    await user.click(screen.getByLabelText("kp.manage.booking_delete_force"));
    await user.click(submit);

    await waitFor(() =>
      expect(deletions).toEqual([{ bookingId: zetaBookingId, force: "true" }]),
    );
  });

  it("deletes a finalized booking without the extra confirmation", async () => {
    const deletions: { bookingId: string; force: string | null }[] = [];
    server.use(
      http.delete(
        `${testBackendUrl}/api/kp/bookings/:bookingId`,
        ({ params, request }) => {
          deletions.push({
            bookingId: String(params.bookingId),
            force: new URL(request.url).searchParams.get("force"),
          });
          return HttpResponse.json(null);
        },
      ),
    );
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    await openRowMenu(user, 0);
    await user.click(
      await screen.findByRole("menuitem", {
        name: "kp.manage.booking_action_delete",
      }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "kp.manage.booking_delete_submit",
      }),
    );

    await waitFor(() =>
      expect(deletions).toEqual([{ bookingId: acmeBookingId, force: "false" }]),
    );
  });

  it("accepts every selected finalized booking at once", async () => {
    const accepted: string[] = [];
    server.use(
      http.post(
        `${testBackendUrl}/api/kp/bookings/:bookingId/accept`,
        ({ params }) => {
          accepted.push(String(params.bookingId));
          return HttpResponse.json(acmeBooking);
        },
      ),
    );
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    await user.click(screen.getByLabelText("kp.manage.bookings_select_all"));
    await user.click(
      screen.getByRole("button", {
        name: "kp.manage.bookings_accept_selected",
      }),
    );

    await waitFor(() => expect(accepted).toEqual([acmeBookingId]));
    expect(notificationsShow).toHaveBeenCalledWith({
      color: "green",
      message: "kp.manage.bookings_accepted",
    });
  });

  it("saves an edited booth number through the booking patch", async () => {
    const patches: { bookingId: string; body: unknown }[] = [];
    server.use(
      http.patch(
        `${testBackendUrl}/api/kp/bookings/:bookingId`,
        async ({ params, request }) => {
          patches.push({
            bookingId: String(params.bookingId),
            body: await request.json(),
          });
          return HttpResponse.json(acmeBooking);
        },
      ),
    );
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    const boothInputs = screen.getAllByLabelText("kp.manage.booking_booth_nr");
    await user.clear(boothInputs[0]);
    await user.type(boothInputs[0], "12");
    await user.tab();

    await waitFor(() =>
      expect(patches).toEqual([
        { bookingId: acmeBookingId, body: { booth_nr: 12 } },
      ]),
    );
  });

  it("downloads the booking export", async () => {
    let exported = false;
    server.use(
      http.get(
        `${testBackendUrl}/api/kp/events/:eventId/exports/bookings/download`,
        () => {
          exported = true;
          return HttpResponse.text("company\n");
        },
      ),
    );
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    await user.click(
      screen.getByRole("button", { name: "kp.manage.bookings_export_csv" }),
    );

    await waitFor(() => expect(exported).toBe(true));
  });
});
