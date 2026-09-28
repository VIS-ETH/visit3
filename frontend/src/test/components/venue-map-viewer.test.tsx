import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import VenueMapViewer from "../../components/venue/VenueMapViewer";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import i18n from "../i18n";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import mainHallPlan from "../../assets/venue/main-hall.webp";
import {
  testMainZone,
  testSecondVenueLayout,
  testSideZone,
  testVenueMap,
} from "../fixtures/venue";

const venueUrl = `${testBackendUrl}/api/kp/events/${testEventId}/venue`;

let venueResponse = testVenueMap;

beforeAll(() => {
  i18n.addResource("en", "common", "kp.booth_size", "{{size}} m²");
});

beforeEach(() => {
  venueResponse = testVenueMap;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(venueUrl, () => HttpResponse.json(venueResponse)),
  );
});

describe("the venue map viewer", () => {
  it("renders every zone as a map button and in the legend", async () => {
    renderWithProviders(<VenueMapViewer eventId={testEventId} />);

    expect(
      await screen.findByRole("button", { name: testMainZone.name }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: testSideZone.name }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(testMainZone.name).length).toBeGreaterThan(1);
    expect(screen.getAllByText(`${testMainZone.booth_size} m²`)).toHaveLength(
      2,
    );
  });

  it("marks a zone without free spots as full", async () => {
    renderWithProviders(<VenueMapViewer eventId={testEventId} />);

    await screen.findByRole("button", { name: testSideZone.name });
    expect(screen.getAllByText("kp.venue.zone_full").length).toBe(2);
  });

  it("selects a zone when its shape is clicked", async () => {
    const onSelectZone = vi.fn();
    const { user } = renderWithProviders(
      <VenueMapViewer eventId={testEventId} onSelectZone={onSelectZone} />,
    );

    await user.click(
      await screen.findByRole("button", { name: testMainZone.name }),
    );

    expect(onSelectZone).toHaveBeenCalledWith(testMainZone.id);
  });

  it("selects a full zone so the waitlist stays reachable", async () => {
    const onSelectZone = vi.fn();
    const { user } = renderWithProviders(
      <VenueMapViewer eventId={testEventId} onSelectZone={onSelectZone} />,
    );

    await user.click(
      await screen.findByRole("button", { name: testSideZone.name }),
    );

    expect(onSelectZone).toHaveBeenCalledWith(testSideZone.id);
  });

  it("selects a zone from the keyboard", async () => {
    const onSelectZone = vi.fn();
    const { user } = renderWithProviders(
      <VenueMapViewer eventId={testEventId} onSelectZone={onSelectZone} />,
    );

    const shape = await screen.findByRole("button", {
      name: testMainZone.name,
    });
    shape.focus();
    await user.keyboard("{Enter}");

    expect(onSelectZone).toHaveBeenCalledWith(testMainZone.id);
  });

  it("offers a layout switcher when the event has several layouts", async () => {
    venueResponse = {
      ...testVenueMap,
      layouts: [...testVenueMap.layouts, testSecondVenueLayout],
    };
    renderWithProviders(<VenueMapViewer eventId={testEventId} />);

    expect(
      await screen.findByRole("radio", { name: testSecondVenueLayout.name }),
    ).toBeInTheDocument();
  });

  it("draws the bundled floor plan of the layout", async () => {
    const [layout] = testVenueMap.layouts;
    venueResponse = {
      ...testVenueMap,
      layouts: [{ ...layout, floor_plan: "main_hall" }],
    };
    const { container } = renderWithProviders(
      <VenueMapViewer eventId={testEventId} />,
    );

    await screen.findByRole("button", { name: testMainZone.name });

    expect(container.querySelector("image")).toHaveAttribute(
      "href",
      mainHallPlan,
    );
    expect(
      screen.getByRole("group", { name: "kp.venue.map_label" }),
    ).toHaveStyle({ color: "var(--mantine-color-black)" });
  });

  it("leaves the zone names to the printed floor plan", async () => {
    const [layout] = testVenueMap.layouts;
    venueResponse = {
      ...testVenueMap,
      layouts: [{ ...layout, floor_plan: "main_hall" }],
    };
    renderWithProviders(<VenueMapViewer eventId={testEventId} />);

    const shape = await screen.findByRole("button", {
      name: testMainZone.name,
    });
    expect(shape.querySelectorAll("text")).toHaveLength(0);
    expect(shape.querySelector("title")).toHaveTextContent(
      `${testMainZone.name} · ${testMainZone.booth_size} m²`,
    );
    expect(screen.getAllByText(`${testMainZone.booth_size} m²`)).toHaveLength(
      1,
    );
  });

  it("hatches a full zone on the floor plan", async () => {
    const [layout] = testVenueMap.layouts;
    venueResponse = {
      ...testVenueMap,
      layouts: [{ ...layout, floor_plan: "main_hall" }],
    };
    renderWithProviders(<VenueMapViewer eventId={testEventId} />);

    const fullShape = await screen.findByRole("button", {
      name: testSideZone.name,
    });
    const freeShape = screen.getByRole("button", { name: testMainZone.name });

    expect(fullShape.querySelector("[data-full-hatch]")).not.toBeNull();
    expect(freeShape.querySelector("[data-full-hatch]")).toBeNull();
    expect(fullShape.querySelector("title")).toHaveTextContent(
      `${testSideZone.name} · kp.venue.zone_full`,
    );
  });

  it("keeps the zone labels on a map without a floor plan", async () => {
    renderWithProviders(<VenueMapViewer eventId={testEventId} />);

    await screen.findByRole("button", { name: testMainZone.name });
    const map = screen.getByRole("group", { name: "kp.venue.map_label" });

    expect(
      Array.from(map.querySelectorAll("text")).map((text) => text.textContent),
    ).toContain(testMainZone.name);
  });

  it("ignores an uploaded background", async () => {
    const [layout] = testVenueMap.layouts;
    venueResponse = {
      ...testVenueMap,
      layouts: [
        { ...layout, background_url: "https://files.test/background.png" },
      ],
    };
    const { container } = renderWithProviders(
      <VenueMapViewer eventId={testEventId} />,
    );

    await screen.findByRole("button", { name: testMainZone.name });

    expect(container.querySelector("image")).toBeNull();
  });

  it("explains when the event has no layout yet", async () => {
    venueResponse = { ...testVenueMap, layouts: [] };
    renderWithProviders(<VenueMapViewer eventId={testEventId} />);

    expect(await screen.findByText("kp.venue.no_layouts")).toBeInTheDocument();
  });
});
