import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import KpBookingZoneSelector from "../../components/exhibitor-booking/KpBookingZoneSelector";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/kp/events/e1/booth-zones/available`, () =>
      HttpResponse.json({ code: "server.error" }, { status: 500 }),
    ),
  );
});

describe("the booking zone selector", () => {
  it("shows a load error instead of claiming that no spots are left", async () => {
    renderWithProviders(
      <KpBookingZoneSelector
        eventId="e1"
        currentBooking={null}
        selectedZone={null}
        onSelectZone={() => {}}
      />,
    );

    expect(await screen.findByText("error.load_failed")).toBeInTheDocument();
    expect(screen.queryByText("kp.booking.zone_no_spots")).toBeNull();
  });
});
