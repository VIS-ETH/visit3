import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { KpBookingStatus } from "../../orval/generated/fastAPI.schemas";
import { KpBookingStatusBadge } from "../../components/KpBookingStatusBadge";
import { KpBookingStatusHelp } from "../../components/KpBookingStatusHelp";
import { renderWithProviders } from "../render";

describe("the booking status badge", () => {
  it("renders a translated label instead of the raw status", () => {
    renderWithProviders(
      <KpBookingStatusBadge status={KpBookingStatus.CONFIRMED} />,
    );

    expect(
      screen.getByText("kp.booking.status.confirmed.label"),
    ).toBeInTheDocument();
    expect(screen.queryByText("CONFIRMED")).not.toBeInTheDocument();
  });

  it("explains every status with the shared labels", async () => {
    const { user } = renderWithProviders(<KpBookingStatusHelp />);

    await user.click(
      screen.getByRole("button", { name: "kp.booking.status_help_open_label" }),
    );

    for (const status of [
      "registered",
      "confirmed",
      "cancelled",
      "rejected",
    ]) {
      expect(
        await screen.findByText(`kp.booking.status.${status}.label`),
      ).toBeInTheDocument();
      expect(
        screen.getByText(`kp.booking.status.${status}.description`),
      ).toBeInTheDocument();
    }
  });
});
