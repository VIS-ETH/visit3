import { describe, expect, it } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import VenueLayoutEditor from "../../components/venue/VenueLayoutEditor";
import type { BoothZoneResponse } from "../../orval/generated/fastAPI.schemas";
import { renderWithProviders } from "../render";
import redHallPlan from "../../assets/venue/red-hall.webp";
import { testEditableLayout, testMainZone } from "../fixtures/venue";

const zones: BoothZoneResponse[] = [
  {
    id: testMainZone.id,
    event_id: testMainZone.event_id,
    name: testMainZone.name,
    description: testMainZone.description,
    color: testMainZone.color,
    order: testMainZone.order,
    booth_size: testMainZone.booth_size,
    base_price: testMainZone.base_price,
    included_services: [],
  },
];

const renderEditor = () =>
  renderWithProviders(
    <VenueLayoutEditor layout={testEditableLayout} zones={zones} />,
  );

const canvas = () => screen.getByRole("group", { name: "kp.venue.map_label" });

const pointerAt = (target: Element, type: string, x: number, y: number) =>
  fireEvent[type as "pointerDown"](target, {
    clientX: x,
    clientY: y,
    pointerId: 1,
  });

const drawRectangle = async (
  user: ReturnType<typeof renderWithProviders>["user"],
) => {
  await user.click(screen.getByRole("radio", { name: "kp.venue.tool_rect" }));
  const svg = canvas();
  pointerAt(svg, "pointerDown", 100, 100);
  pointerAt(svg, "pointerMove", 300, 250);
  pointerAt(svg, "pointerUp", 300, 250);
};

describe("the venue layout editor", () => {
  it("draws the zones over the bundled floor plan", () => {
    const { container } = renderWithProviders(
      <VenueLayoutEditor
        layout={{ ...testEditableLayout, floor_plan: "red_hall" }}
        zones={zones}
      />,
    );

    expect(container.querySelector("image")).toHaveAttribute(
      "href",
      redHallPlan,
    );
  });

  it("draws a rectangle from a pointer drag", async () => {
    const { user } = renderEditor();

    await drawRectangle(user);

    const shape = screen.getByRole("button", { name: testMainZone.name });
    const rect = shape.querySelector("rect");
    expect(rect).toHaveAttribute("x", "100");
    expect(rect).toHaveAttribute("y", "100");
    expect(rect).toHaveAttribute("width", "200");
    expect(rect).toHaveAttribute("height", "150");
  });

  it("ignores a drag that stays inside one grid cell", async () => {
    const { user } = renderEditor();

    await user.click(screen.getByRole("radio", { name: "kp.venue.tool_rect" }));
    const svg = canvas();
    pointerAt(svg, "pointerDown", 100, 100);
    pointerAt(svg, "pointerUp", 102, 102);

    expect(
      screen.queryByRole("button", { name: testMainZone.name }),
    ).not.toBeInTheDocument();
  });

  it("closes a polygon when Enter is pressed", async () => {
    const { user } = renderEditor();

    await user.click(
      screen.getByRole("radio", { name: "kp.venue.tool_polygon" }),
    );
    const svg = canvas();
    pointerAt(svg, "pointerDown", 100, 100);
    pointerAt(svg, "pointerDown", 300, 100);
    pointerAt(svg, "pointerDown", 300, 300);
    fireEvent.keyDown(window, { key: "Enter" });

    const shape = screen.getByRole("button", { name: testMainZone.name });
    expect(shape.querySelector("polygon")).toHaveAttribute(
      "points",
      "100,100 300,100 300,300",
    );
  });

  it("drops a pending polygon when Escape is pressed", async () => {
    const { user } = renderEditor();

    await user.click(
      screen.getByRole("radio", { name: "kp.venue.tool_polygon" }),
    );
    const svg = canvas();
    pointerAt(svg, "pointerDown", 100, 100);
    pointerAt(svg, "pointerDown", 300, 100);
    pointerAt(svg, "pointerDown", 300, 300);
    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent.keyDown(window, { key: "Enter" });

    expect(
      screen.queryByRole("button", { name: testMainZone.name }),
    ).not.toBeInTheDocument();
  });

  it("removes the last drawn shape when undo is used", async () => {
    const { user } = renderEditor();

    await drawRectangle(user);
    expect(
      screen.getByRole("button", { name: testMainZone.name }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "kp.venue.undo" }));

    expect(
      screen.queryByRole("button", { name: testMainZone.name }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "kp.venue.redo" }));

    expect(
      screen.getByRole("button", { name: testMainZone.name }),
    ).toBeInTheDocument();
  });

  it("numbers placed booths upwards", async () => {
    const { user } = renderEditor();

    await user.click(
      screen.getByRole("radio", { name: "kp.venue.tool_booth" }),
    );
    const svg = canvas();
    pointerAt(svg, "pointerDown", 200, 200);
    pointerAt(svg, "pointerDown", 400, 300);

    expect(
      screen.getByRole("button", {
        name: `kp.venue.booth_marker 1 ${testMainZone.name}`,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: `kp.venue.booth_marker 2 ${testMainZone.name}`,
      }),
    ).toBeInTheDocument();
  });

  it("renames the selected booth", async () => {
    const { user } = renderEditor();

    await user.click(
      screen.getByRole("radio", { name: "kp.venue.tool_booth" }),
    );
    pointerAt(canvas(), "pointerDown", 200, 200);
    const number = screen.getByLabelText("kp.venue.booth_number");
    await user.clear(number);
    await user.type(number, "17");

    expect(
      screen.getByRole("button", {
        name: `kp.venue.booth_marker 17 ${testMainZone.name}`,
      }),
    ).toBeInTheDocument();
  });

  it("deletes the selected booth", async () => {
    const { user } = renderEditor();

    await user.click(
      screen.getByRole("radio", { name: "kp.venue.tool_booth" }),
    );
    pointerAt(canvas(), "pointerDown", 200, 200);
    await user.click(
      screen.getByRole("button", { name: "kp.venue.delete_selected" }),
    );

    expect(
      screen.queryByRole("button", {
        name: `kp.venue.booth_marker 1 ${testMainZone.name}`,
      }),
    ).not.toBeInTheDocument();
  });

  it("deletes the selected shape", async () => {
    const { user } = renderEditor();

    await drawRectangle(user);
    await user.click(
      screen.getByRole("button", { name: "kp.venue.delete_selected" }),
    );

    expect(
      screen.queryByRole("button", { name: testMainZone.name }),
    ).not.toBeInTheDocument();
  });
});
