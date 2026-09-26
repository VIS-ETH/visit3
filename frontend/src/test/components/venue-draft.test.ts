import { describe, expect, it } from "vitest";
import {
  boothsRequest,
  shapesRequest,
} from "../../components/venue/venue-draft";

describe("the venue save requests", () => {
  it("rounds every coordinate to one decimal", () => {
    const draft = {
      shapes: [
        {
          key: "polygon",
          zoneId: "zone-1",
          shape: {
            type: "polygon" as const,
            points: [
              [10.123456, 20.987654],
              [30.05, 40.04],
              [50, 60.66666],
            ] as [number, number][],
          },
          labelPosition: [12.3456, 7.891] as [number, number],
        },
        {
          key: "rect",
          zoneId: "zone-1",
          shape: {
            type: "rect" as const,
            x: 1.234,
            y: 5.678,
            w: 9.99,
            h: 0.44,
          },
          labelPosition: null,
        },
      ],
      booths: [
        {
          key: "booth",
          zoneId: "zone-1",
          boothNr: 1,
          x: 3.14159,
          y: 2.71828,
          rotation: 12.3456,
        },
      ],
    };

    expect(shapesRequest(draft)).toEqual({
      shapes: [
        {
          booth_zone_id: "zone-1",
          shape: {
            type: "polygon",
            points: [
              [10.1, 21],
              [30.1, 40],
              [50, 60.7],
            ],
          },
          label_position: [12.3, 7.9],
        },
        {
          booth_zone_id: "zone-1",
          shape: { type: "rect", x: 1.2, y: 5.7, w: 10, h: 0.4 },
          label_position: null,
        },
      ],
    });
    expect(boothsRequest(draft)).toEqual({
      booths: [
        {
          booth_zone_id: "zone-1",
          booth_nr: 1,
          x: 3.1,
          y: 2.7,
          rotation: 12.3,
        },
      ],
    });
  });
});
