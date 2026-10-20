import { beforeEach, describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import BookingsTab from "../../components/BookingsTab";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { KpServiceCategory } from "../../orval/generated/fastAPI.schemas";
import {
  acmeBooking,
  staffBookings,
  testSideHallZoneId,
} from "../fixtures/staff-bookings";

const companyOrder = () =>
  screen.getAllByRole("link").map((link) => link.textContent);

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/bookings`, () =>
      HttpResponse.json(staffBookings),
    ),
  );
});

describe("the staff bookings table", () => {
  it("searches by company name", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    await user.type(
      screen.getByPlaceholderText("kp.manage.bookings_search_placeholder"),
      "bet",
    );

    expect(companyOrder()).toEqual(["Beta GmbH"]);
  });

  it("filters by status", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    await user.click(
      screen.getByRole("combobox", {
        name: "kp.manage.bookings_filter_status",
      }),
    );
    await user.click(
      await screen.findByRole("option", {
        name: "kp.booking.status.confirmed.label",
      }),
    );

    expect(companyOrder()).toEqual(["Zeta SA"]);
  });

  it("filters by booked service or service category", async () => {
    const barTable = {
      ...acmeBooking.services![0],
      id: "bar-table-booking-service",
      service_id: "bar-table",
      service: {
        ...acmeBooking.services![0].service,
        id: "bar-table",
        name: "Bar table",
        category: KpServiceCategory.BOOTH_ELEMENT,
      },
    };
    server.use(
      http.get(`${testBackendUrl}/api/kp/events/:eventId/bookings`, () =>
        HttpResponse.json(
          staffBookings.map((booking) =>
            booking.company.name === "Zeta SA"
              ? { ...booking, services: [...booking.services!, barTable] }
              : booking,
          ),
        ),
      ),
    );
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    const [filter] = screen
      .getAllByLabelText("kp.manage.bookings_filter_services")
      .filter((element) => (element as HTMLInputElement).type !== "hidden");
    await user.click(filter);
    await user.click(
      await screen.findByRole("option", {
        name: "kp.manage.service_filter_any_booth_element",
      }),
    );

    expect(companyOrder()).toEqual(["Zeta SA"]);

    await user.click(
      await screen.findByRole("option", { name: "Booth package" }),
    );

    expect(companyOrder()).toEqual(["Acme AG", "Beta GmbH", "Zeta SA"]);
  });

  it("filters by booth zone", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    const [filter] = screen
      .getAllByLabelText("kp.manage.bookings_filter_zones")
      .filter((element) => (element as HTMLInputElement).type !== "hidden");
    await user.click(filter);
    await user.click(await screen.findByRole("option", { name: "Main hall" }));

    expect(companyOrder()).toEqual(["Acme AG", "Zeta SA"]);
  });

  it("filters down to the incomplete bookings", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    await user.click(
      screen.getByLabelText("kp.manage.bookings_filter_incomplete"),
    );

    expect(companyOrder()).toEqual(["Beta GmbH"]);
  });

  it("sorts by company and flips the direction on a second click", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    expect(companyOrder()).toEqual(["Acme AG", "Beta GmbH", "Zeta SA"]);

    await user.click(screen.getByText("kp.manage.booking_company"));

    expect(companyOrder()).toEqual(["Zeta SA", "Beta GmbH", "Acme AG"]);
  });

  it("sorts by booth zone", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    await user.click(screen.getByText("kp.manage.booking_booth_zone"));

    expect(companyOrder()).toEqual(["Acme AG", "Zeta SA", "Beta GmbH"]);
  });

  it("sorts by booth zone along the zone order", async () => {
    server.use(
      http.get(`${testBackendUrl}/api/kp/events/:eventId/bookings`, () =>
        HttpResponse.json(
          staffBookings.map((booking) =>
            booking.booth_zone_id === testSideHallZoneId
              ? { ...booking, booth_zone: { ...booking.booth_zone, order: 0 } }
              : booking,
          ),
        ),
      ),
    );
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    await user.click(screen.getByText("kp.manage.booking_booth_zone"));

    expect(companyOrder()).toEqual(["Beta GmbH", "Acme AG", "Zeta SA"]);
  });

  it("sorts by booth number with unassigned booths last", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    await user.click(screen.getByText("kp.manage.booking_booth_nr"));

    expect(companyOrder()).toEqual(["Acme AG", "Zeta SA", "Beta GmbH"]);

    await user.click(screen.getByText("kp.manage.booking_booth_nr"));

    expect(companyOrder()).toEqual(["Zeta SA", "Acme AG", "Beta GmbH"]);
  });

  it("sorts by the waiting list", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    await user.click(screen.getByText("kp.manage.booking_waitlist"));
    await user.click(screen.getByText("kp.manage.booking_waitlist"));

    expect(companyOrder()[0]).toBe("Beta GmbH");
  });

  it("sorts by status along the booking lifecycle", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    await user.click(screen.getByText("kp.manage.booking_status"));

    expect(companyOrder()).toEqual(["Acme AG", "Beta GmbH", "Zeta SA"]);
  });

  it("renders every row when the list carries no download urls", async () => {
    renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });

    expect(
      staffBookings.every(
        (booking) =>
          booking.booth_zone.layout_url === null &&
          (booking.services ?? []).every(
            (bookingService) => bookingService.service.image_url === null,
          ),
      ),
    ).toBe(true);
    expect(companyOrder()).toEqual(["Acme AG", "Beta GmbH", "Zeta SA"]);
    const table = within(screen.getByRole("table"));
    expect(table.getAllByText("Main hall")).toHaveLength(2);
    expect(table.getByText("Side hall")).toBeInTheDocument();
  });

  it("explains what is missing on an incomplete booking", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText("Beta GmbH", {}, { timeout: 5000 });
    await user.hover(screen.getByLabelText("kp.manage.booking_incomplete"));

    const tooltip = await screen.findByRole("tooltip");
    expect(
      within(tooltip).getByText(
        "kp.manage.booking_missing_item_company_profile",
      ),
    ).toBeInTheDocument();
    expect(
      within(tooltip).getByText("Booth package · Company brochure"),
    ).toBeInTheDocument();
  });
});
