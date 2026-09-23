import { beforeAll, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { KpBookingRecap } from "../../components/KpBookingRecap";
import { KpBookingStatus } from "../../orval/generated/fastAPI.schemas";
import type { BookingResponse } from "../../orval/generated/fastAPI.schemas";
import i18n from "../i18n";
import { renderWithProviders } from "../render";

const booking: BookingResponse = {
  id: "booking-1",
  booking_number: 1,
  event_id: "event-1",
  company_id: "company-1",
  booth_zone_id: "zone-1",
  booth_nr: null,
  status: KpBookingStatus.REGISTERED,
  booth_zone: {
    id: "zone-1",
    event_id: "event-1",
    name: "Main Hall",
    description: "",
    color: "#112233",
    order: 1,
    capacity: 10,
    booth_size: 4,
    base_price: 100000,
    included_services: [],
  },
  additional_service_charges: [
    {
      name: "Power Socket",
      quantity: 3,
      charged_quantity: 2,
      line_net: 5000,
    },
  ],
  price: { net: 105000, vat: 8505, gross: 113505 },
};

beforeAll(() => {
  i18n.addResource(
    "en",
    "common",
    "kp.booking.service_included_note",
    "{{included}} included",
  );
});

describe("KpBookingRecap", () => {
  it("labels a partly included charge with the charged and included quantity", () => {
    renderWithProviders(<KpBookingRecap booking={booking} />);

    expect(
      screen.getByText("Power Socket × 2 (1 included)"),
    ).toBeInTheDocument();
  });

  it("labels a fully charged single unit without a quantity suffix", () => {
    renderWithProviders(
      <KpBookingRecap
        booking={{
          ...booking,
          additional_service_charges: [
            {
              name: "Power Socket",
              quantity: 1,
              charged_quantity: 1,
              line_net: 2500,
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("Power Socket")).toBeInTheDocument();
  });

  it("adds the charges to the booth zone base price", () => {
    renderWithProviders(<KpBookingRecap booking={booking} />);

    expect(screen.getByText("CHF 1000.00")).toBeInTheDocument();
    expect(screen.getByText("CHF 50.00")).toBeInTheDocument();
    expect(screen.getByText("CHF 1050.00")).toBeInTheDocument();
  });
});
