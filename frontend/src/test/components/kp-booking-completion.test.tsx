import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { KpBookingCompletion } from "../../components/KpBookingCompletion";
import { KpBookingStatus } from "../../orval/generated/fastAPI.schemas";
import type { BookingResponse } from "../../orval/generated/fastAPI.schemas";
import { renderWithProviders } from "../render";
import {
  testBooking,
  testBookingId,
  testEventId,
  testFileRequirementId,
  testTextRequirementId,
} from "../fixtures/kp-booking";

const openDeadline = "2099-12-31";
const passedDeadline = "2000-01-01";
const profileLink = (fieldId: string) =>
  `/company/profile?next=%2Fkp%2Fevent#${fieldId}`;

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
    renderWithProviders(
      <KpBookingCompletion
        booking={incompleteBooking}
        changeDeadline={openDeadline}
      />,
    );

    expect(
      screen.getByText("kp.booking.completeness_incomplete"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Booth package · Company brochure"),
    ).toBeInTheDocument();
  });

  it("links the profile and billing items to their profile fields", () => {
    renderWithProviders(
      <KpBookingCompletion
        booking={incompleteBooking}
        changeDeadline={openDeadline}
      />,
      { route: "/kp/event" },
    );

    expect(
      screen.getByRole("link", {
        name: "kp.booking.missing_item_company_profile",
      }),
    ).toHaveAttribute("href", profileLink("company-profile-description"));
    expect(
      screen.getByRole("link", {
        name: "kp.booking.missing_item_billing_address",
      }),
    ).toHaveAttribute(
      "href",
      profileLink("company-profile-billing-company-name"),
    );
  });

  it("links a missing requirement to its field on the services page", () => {
    renderWithProviders(
      <KpBookingCompletion
        booking={incompleteBooking}
        changeDeadline={openDeadline}
      />,
    );

    expect(
      screen.getByRole("link", { name: "Booth package · Company brochure" }),
    ).toHaveAttribute(
      "href",
      `/kp/${testEventId}/booking/${testBookingId}/manage/services#booking-requirement-${testFileRequirementId}`,
    );
  });

  it("states the change deadline while it is open", () => {
    renderWithProviders(
      <KpBookingCompletion
        booking={incompleteBooking}
        changeDeadline={openDeadline}
      />,
    );

    expect(
      screen.getByText("kp.booking.completeness_deadline"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("error.kp_finalization_deadline_passed"),
    ).not.toBeInTheDocument();
  });

  it("shows the locked wording once the change deadline passed", () => {
    renderWithProviders(
      <KpBookingCompletion
        booking={incompleteBooking}
        changeDeadline={passedDeadline}
      />,
    );

    expect(
      screen.getByText("error.kp_finalization_deadline_passed"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("kp.booking.completeness_deadline"),
    ).not.toBeInTheDocument();
  });

  it("states no deadline for a complete booking", () => {
    renderWithProviders(
      <KpBookingCompletion
        booking={completeBooking}
        changeDeadline={openDeadline}
      />,
    );

    expect(
      screen.queryByText("kp.booking.completeness_deadline"),
    ).not.toBeInTheDocument();
  });

  it("links a missing description to its profile field", () => {
    renderWithProviders(
      <KpBookingCompletion
        changeDeadline={openDeadline}
        booking={{
          ...incompleteBooking,
          missing_items: ["company_description"],
        }}
      />,
      { route: "/kp/event" },
    );

    expect(
      screen.getByRole("link", {
        name: "kp.booking.missing_item_company_description",
      }),
    ).toHaveAttribute("href", profileLink("company-profile-description"));
  });

  it("links a missing general email to its profile field", () => {
    renderWithProviders(
      <KpBookingCompletion
        changeDeadline={openDeadline}
        booking={{
          ...incompleteBooking,
          missing_items: ["general_email"],
        }}
      />,
      { route: "/kp/event" },
    );

    expect(
      screen.getByRole("link", {
        name: "kp.booking.missing_item_general_email",
      }),
    ).toHaveAttribute("href", profileLink("company-profile-general-email"));
  });

  it("falls back to a generic label for an unknown requirement", () => {
    renderWithProviders(
      <KpBookingCompletion
        changeDeadline={openDeadline}
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
    renderWithProviders(
      <KpBookingCompletion
        booking={completeBooking}
        changeDeadline={openDeadline}
      />,
    );

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
        changeDeadline={openDeadline}
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

  it("explains confirmed bookings", () => {
    renderWithProviders(
      <KpBookingCompletion
        changeDeadline={openDeadline}
        booking={{ ...completeBooking, status: KpBookingStatus.CONFIRMED }}
      />,
    );
    expect(screen.getByText("kp.booking.confirmed_title")).toBeInTheDocument();
  });

  it("keeps the requirement lookup stable across several booked services", () => {
    renderWithProviders(
      <KpBookingCompletion
        changeDeadline={openDeadline}
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
