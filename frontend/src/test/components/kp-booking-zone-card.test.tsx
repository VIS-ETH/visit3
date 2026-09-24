import { beforeAll, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import KpBookingZoneCard from "../../components/KpBookingZoneCard";
import i18n from "../i18n";
import { renderWithProviders } from "../render";
import { testMainZone, testSideZone } from "../fixtures/venue";

const renderCard = (zone = testMainZone) =>
  renderWithProviders(
    <KpBookingZoneCard
      zone={zone}
      isSelected={false}
      isDisabled={zone.is_full}
      onSelect={vi.fn()}
    />,
  );

beforeAll(() => {
  i18n.addResource("en", "common", "kp.booth_size", "{{size}} m²");
});

describe("the booking zone card", () => {
  it("shows the booth size instead of the free spots", () => {
    renderCard();

    expect(screen.getByRole("button")).toHaveTextContent(
      `${testMainZone.booth_size} m²`,
    );
    expect(screen.getByRole("button")).not.toHaveTextContent(
      String(testMainZone.capacity),
    );
  });

  it("marks a full zone as fully booked", () => {
    renderCard(testSideZone);

    expect(screen.getByRole("button")).toHaveTextContent(
      "kp.booking.zone_full",
    );
    expect(screen.getByRole("button")).not.toHaveTextContent("m²");
  });
});
