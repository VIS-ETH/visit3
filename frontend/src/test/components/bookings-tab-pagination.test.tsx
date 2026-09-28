import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import BookingsTab from "../../components/BookingsTab";
import type { StaffBookingResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { acmeBooking } from "../fixtures/staff-bookings";

const PAGE_SIZE = 25;
const TOTAL = 30;

const companyName = (index: number) =>
  `Company ${String(index).padStart(2, "0")}`;

const manyBookings: StaffBookingResponse[] = Array.from(
  { length: TOTAL },
  (_unused, index): StaffBookingResponse => ({
    ...acmeBooking,
    id: `booking-${index}`,
    booking_number: index + 1,
    company: { id: `company-${index}`, name: companyName(index) },
    company_id: `company-${index}`,
  }),
);

const companyOrder = () =>
  screen.getAllByRole("link").map((link) => link.textContent);

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/bookings`, () =>
      HttpResponse.json(manyBookings),
    ),
  );
});

describe("the staff bookings pagination", () => {
  it("shows one page of sorted bookings at a time", async () => {
    renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText(companyName(0), {}, { timeout: 5000 });

    expect(companyOrder()).toHaveLength(PAGE_SIZE);
    expect(companyOrder()[0]).toBe(companyName(0));
    expect(screen.queryByText(companyName(PAGE_SIZE))).not.toBeInTheDocument();
  });

  it("shows the remaining bookings on the next page", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText(companyName(0), {}, { timeout: 5000 });
    await user.click(screen.getByRole("button", { name: "2" }));

    expect(companyOrder()).toHaveLength(TOTAL - PAGE_SIZE);
    expect(companyOrder()[0]).toBe(companyName(PAGE_SIZE));
    expect(screen.queryByText(companyName(0))).not.toBeInTheDocument();
  });

  it("sorts across every page before paging", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText(companyName(0), {}, { timeout: 5000 });
    await user.click(
      screen.getByRole("button", { name: "kp.manage.booking_company" }),
    );

    expect(companyOrder()[0]).toBe(companyName(TOTAL - 1));
  });

  it("returns to the first page when the search narrows the list", async () => {
    const { user } = renderWithProviders(<BookingsTab eventId={testEventId} />);

    await screen.findByText(companyName(0), {}, { timeout: 5000 });
    await user.click(screen.getByRole("button", { name: "2" }));
    await user.type(
      screen.getByPlaceholderText("kp.manage.bookings_search_placeholder"),
      "company 2",
    );

    expect(companyOrder()[0]).toBe(companyName(20));
    expect(companyOrder()).toHaveLength(10);
    expect(screen.queryByRole("button", { name: "2" })).not.toBeInTheDocument();
  });
});
