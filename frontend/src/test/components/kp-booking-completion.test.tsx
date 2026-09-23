import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { KpBookingCompletion } from "../../components/KpBookingCompletion";
import { KpBookingStatus } from "../../orval/generated/fastAPI.schemas";
import type { BookingResponse } from "../../orval/generated/fastAPI.schemas";
import { renderWithProviders } from "../render";
import {
  testBooking,
  testFileRequirementId,
  testTextRequirementId,
} from "../fixtures/kp-booking";

const incompleteBooking: BookingResponse = {
  ...testBooking,
  is_complete: false,
  missing_items: [
    `requirement:${testFileRequirementId}`,
    "company_profile",
    "billing_address",
  ],
};

const completeBooking: BookingResponse = {
  ...testBooking,
  is_complete: true,
  missing_items: [],
};

describe("KpBookingCompletion", () => {
  it("names the service and requirement behind a missing requirement item", () => {
    renderWithProviders(<KpBookingCompletion booking={incompleteBooking} />);

    expect(
      screen.getByText("kp.booking.completeness_incomplete"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Booth package · Company brochure"),
    ).toBeInTheDocument();
  });

  it("links the profile and billing items to the company profile", () => {
    renderWithProviders(<KpBookingCompletion booking={incompleteBooking} />);

    expect(
      screen.getByRole("link", {
        name: "kp.booking.missing_item_company_profile",
      }),
    ).toHaveAttribute("href", "/company/profile");
    expect(
      screen.getByRole("link", {
        name: "kp.booking.missing_item_billing_address",
      }),
    ).toHaveAttribute("href", "/company/profile");
  });

  it("falls back to a generic label for an unknown requirement", () => {
    renderWithProviders(
      <KpBookingCompletion
        booking={{
          ...incompleteBooking,
          missing_items: ["requirement:00000000-0000-0000-0000-000000000000"],
        }}
      />,
    );

    expect(
      screen.getByText("kp.booking.missing_item_requirement"),
    ).toBeInTheDocument();
  });

  it("shows a complete badge and no missing list when nothing is missing", () => {
    renderWithProviders(<KpBookingCompletion booking={completeBooking} />);

    expect(
      screen.getByText("kp.booking.completeness_complete"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("kp.booking.completeness_incomplete"),
    ).not.toBeInTheDocument();
  });

  it("explains a rejected booking together with its reason", () => {
    renderWithProviders(
      <KpBookingCompletion
        booking={{
          ...completeBooking,
          status: KpBookingStatus.REJECTED,
          rejection_reason: "Booth zone is reserved for sponsors",
        }}
      />,
    );

    expect(screen.getByText("kp.booking.rejected_title")).toBeInTheDocument();
    expect(
      screen.getByText("Booth zone is reserved for sponsors"),
    ).toBeInTheDocument();
  });

  it("explains finalized and confirmed bookings", () => {
    const { unmount } = renderWithProviders(
      <KpBookingCompletion
        booking={{ ...completeBooking, status: KpBookingStatus.FINALIZED }}
      />,
    );
    expect(screen.getByText("kp.booking.finalized_title")).toBeInTheDocument();
    unmount();

    renderWithProviders(
      <KpBookingCompletion
        booking={{ ...completeBooking, status: KpBookingStatus.CONFIRMED }}
      />,
    );
    expect(screen.getByText("kp.booking.confirmed_title")).toBeInTheDocument();
  });

  it("keeps the requirement lookup stable across several booked services", () => {
    renderWithProviders(
      <KpBookingCompletion
        booking={{
          ...incompleteBooking,
          missing_items: [`requirement:${testTextRequirementId}`],
        }}
      />,
    );

    expect(
      screen.getByText("Booth package · Company slogan"),
    ).toBeInTheDocument();
  });
});
