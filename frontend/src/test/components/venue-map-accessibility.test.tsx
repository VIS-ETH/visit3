import { beforeEach, describe, expect, it } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import VenueMapViewer from "../../components/venue/VenueMapViewer";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { testMainZone, testSideZone, testVenueMap } from "../fixtures/venue";

const venueUrl = `${testBackendUrl}/api/kp/events/${testEventId}/venue`;

const canvas = () => screen.getByRole("group", { name: "kp.venue.map_label" });

const transformOf = () =>
  canvas().querySelector("g")?.getAttribute("transform") ?? "";

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(venueUrl, () => HttpResponse.json(testVenueMap)),
  );
});

describe("the venue map zones", () => {
  it("expose their selection through aria-pressed", async () => {
    renderWithProviders(
      <VenueMapViewer eventId={testEventId} selectedZoneId={testMainZone.id} />,
    );

    expect(
      await screen.findByRole("button", { name: testMainZone.name }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByRole("button", { name: testSideZone.name }),
    ).toHaveAttribute("aria-pressed", "false");
  });

  it("point at their legend entry", async () => {
    renderWithProviders(<VenueMapViewer eventId={testEventId} />);

    const zone = await screen.findByRole("button", {
      name: testMainZone.name,
    });
    const describedBy = zone.getAttribute("aria-describedby");

    expect(describedBy).toBeTruthy();
    const legendItem = document.getElementById(describedBy ?? "");
    expect(legendItem).not.toBeNull();
    expect(legendItem?.textContent).toContain(testMainZone.name);
  });
});

describe("the venue map booths", () => {
  it("name their number and their zone", async () => {
    renderWithProviders(<VenueMapViewer eventId={testEventId} />);

    const booth = await screen.findByRole("img", {
      name: `kp.venue.booth_marker 1 ${testMainZone.name}`,
    });

    expect(booth).toBeInTheDocument();
  });
});

describe("the venue map keyboard zoom", () => {
  it("zooms in, out and back to the full layout", async () => {
    renderWithProviders(<VenueMapViewer eventId={testEventId} />);

    await screen.findByRole("button", { name: testMainZone.name });
    const initialTransform = transformOf();

    fireEvent.keyDown(canvas(), { key: "+" });
    const zoomedIn = transformOf();
    expect(zoomedIn).not.toBe(initialTransform);

    fireEvent.keyDown(canvas(), { key: "-" });
    expect(transformOf()).not.toBe(zoomedIn);

    fireEvent.keyDown(canvas(), { key: "+" });
    fireEvent.keyDown(canvas(), { key: "0" });
    expect(transformOf()).toBe(initialTransform);
  });

  it("is reachable with the keyboard", async () => {
    renderWithProviders(<VenueMapViewer eventId={testEventId} />);

    await screen.findByRole("button", { name: testMainZone.name });

    expect(canvas()).toHaveAttribute("tabindex", "0");
    expect(canvas()).toHaveAttribute("aria-keyshortcuts");
  });
});
