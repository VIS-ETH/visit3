import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import NametagCard from "../../components/booking/NametagCard";
import {
  KpBookingStatus,
  type BookingResponse,
  type KpResponse,
  type NameTagResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import i18n from "../i18n";
import { createToken } from "../jwt";
import { notificationsShow } from "../notifications";
import { renderWithProviders } from "../render";
import { testBooking, testBookingId, testEvent } from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const openEvent: KpResponse = {
  ...testEvent,
  nametags_deadline: "2099-12-31",
  max_nametags_per_booking: 3,
};

const closedEvent: KpResponse = {
  ...openEvent,
  nametags_deadline: "2000-01-01",
};

const nametagsUrl = `${testBackendUrl}/api/kp/bookings/${testBookingId}/nametags`;

const curieNametag: NameTagResponse = {
  id: "aaaa1111-aaaa-1111-aaaa-111111111111",
  booking_id: testBookingId,
  first_name: "Marie",
  last_name: "Curie",
  position: "Recruiting",
};

const eulerNametag: NameTagResponse = {
  id: "bbbb2222-bbbb-2222-bbbb-222222222222",
  booking_id: testBookingId,
  first_name: "Leonhard",
  last_name: "Euler",
  position: "Engineering",
};

let nametags: NameTagResponse[] = [];

const renderCard = (event: KpResponse = openEvent, booking = testBooking) =>
  renderWithProviders(<NametagCard event={event} booking={booking} />);

const inputs = (name: string) => screen.getAllByLabelText(name);

beforeAll(() => {
  i18n.addResource("en", "common", "kp.nametags.counter", "{{used}} / {{max}}");
  i18n.addResource(
    "en",
    "common",
    "kp.nametags.deadline",
    "Editable until {{date}}",
  );
});

beforeEach(() => {
  nametags = [curieNametag, eulerNametag];
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(nametagsUrl, () => HttpResponse.json(nametags)),
  );
});

describe("the booking nametag editor", () => {
  it("lists the saved nametags with the counter and the deadline", async () => {
    renderCard();

    expect(
      await screen.findByDisplayValue(
        curieNametag.first_name,
        undefined,
        SLOW_WAIT,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByDisplayValue(eulerNametag.last_name),
    ).toBeInTheDocument();
    expect(screen.getByText("2 / 3")).toBeInTheDocument();
    expect(screen.getByText(/^Editable until .*2099/)).toBeInTheDocument();
  });

  it("saves the full list after a row was added", async () => {
    let payload: unknown = null;
    server.use(
      http.put(nametagsUrl, async ({ request }) => {
        payload = await request.json();
        nametags = [
          curieNametag,
          eulerNametag,
          {
            id: "cccc3333-cccc-3333-cccc-333333333333",
            booking_id: testBookingId,
            first_name: "Ada",
            last_name: "Lovelace",
            position: "Software",
          },
        ];
        return HttpResponse.json(nametags);
      }),
    );
    const { user } = renderCard();

    await screen.findByDisplayValue(
      curieNametag.first_name,
      undefined,
      SLOW_WAIT,
    );
    await user.click(screen.getByRole("button", { name: "kp.nametags.add" }));

    await user.type(inputs("kp.nametags.first_name")[2], "Ada");
    await user.type(inputs("kp.nametags.last_name")[2], "Lovelace");
    await user.type(inputs("kp.nametags.position")[2], "Software");

    expect(screen.getByText("kp.nametags.unsaved")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "kp.nametags.save" }));

    await waitFor(() => {
      expect(payload).toEqual({
        name_tags: [
          {
            first_name: "Marie",
            last_name: "Curie",
            position: "Recruiting",
          },
          {
            first_name: "Leonhard",
            last_name: "Euler",
            position: "Engineering",
          },
          {
            first_name: "Ada",
            last_name: "Lovelace",
            position: "Software",
          },
        ],
      });
    }, SLOW_WAIT);
    expect(notificationsShow).toHaveBeenCalledWith(
      expect.objectContaining({ message: "kp.nametags.saved" }),
    );
    await waitFor(() => {
      expect(screen.queryByText("kp.nametags.unsaved")).not.toBeInTheDocument();
    }, SLOW_WAIT);
  });

  it("sends the shortened list after a row was removed", async () => {
    let payload: unknown = null;
    server.use(
      http.put(nametagsUrl, async ({ request }) => {
        payload = await request.json();
        nametags = [eulerNametag];
        return HttpResponse.json(nametags);
      }),
    );
    const { user } = renderCard();

    await screen.findByDisplayValue(
      curieNametag.first_name,
      undefined,
      SLOW_WAIT,
    );
    await user.click(
      screen.getAllByRole("button", { name: "kp.nametags.remove" })[0],
    );
    expect(screen.getByText("1 / 3")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "kp.nametags.save" }));

    await waitFor(() => {
      expect(payload).toEqual({
        name_tags: [
          {
            first_name: "Leonhard",
            last_name: "Euler",
            position: "Engineering",
          },
        ],
      });
    }, SLOW_WAIT);
  });

  it("keeps saving disabled while nothing changed and while a row is incomplete", async () => {
    const { user } = renderCard();

    await screen.findByDisplayValue(
      curieNametag.first_name,
      undefined,
      SLOW_WAIT,
    );
    expect(
      screen.getByRole("button", { name: "kp.nametags.save" }),
    ).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "kp.nametags.add" }));

    expect(screen.getByText("kp.nametags.incomplete")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "kp.nametags.save" }),
    ).toBeDisabled();
  });

  it("stops adding rows once the event limit is reached", async () => {
    const { user } = renderCard();

    await screen.findByDisplayValue(
      curieNametag.first_name,
      undefined,
      SLOW_WAIT,
    );
    await user.click(screen.getByRole("button", { name: "kp.nametags.add" }));

    expect(screen.getByText("3 / 3")).toBeInTheDocument();
    expect(screen.getByText("kp.nametags.limit_reached")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "kp.nametags.add" }),
    ).toBeDisabled();
  });

  it("explains that the list is locked once the deadline passed", async () => {
    renderCard(closedEvent);

    await screen.findByDisplayValue(
      curieNametag.first_name,
      undefined,
      SLOW_WAIT,
    );
    expect(screen.getByText("kp.nametags.deadline_passed")).toBeInTheDocument();
    expect(inputs("kp.nametags.first_name")[0]).toBeDisabled();
    expect(
      screen.queryByRole("button", { name: "kp.nametags.add" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.nametags.save" }),
    ).not.toBeInTheDocument();
  });

  it("explains that a cancelled booking has no editable nametags", async () => {
    const cancelledBooking: BookingResponse = {
      ...testBooking,
      status: KpBookingStatus.CANCELLED,
    };
    renderCard(openEvent, cancelledBooking);

    await screen.findByDisplayValue(
      curieNametag.first_name,
      undefined,
      SLOW_WAIT,
    );
    expect(screen.getByText("kp.nametags.booking_closed")).toBeInTheDocument();
    expect(inputs("kp.nametags.last_name")[0]).toBeDisabled();
    expect(
      screen.queryByRole("button", { name: "kp.nametags.save" }),
    ).not.toBeInTheDocument();
  });

  it("shows a rejected save inline", async () => {
    server.use(
      http.put(nametagsUrl, () =>
        HttpResponse.json(
          { code: "error.kp_nametag_limit_reached" },
          { status: 400 },
        ),
      ),
    );
    const { user } = renderCard();

    await screen.findByDisplayValue(
      curieNametag.first_name,
      undefined,
      SLOW_WAIT,
    );
    await user.click(
      screen.getAllByRole("button", { name: "kp.nametags.remove" })[0],
    );
    await user.click(screen.getByRole("button", { name: "kp.nametags.save" }));

    expect(
      await screen.findByText(
        "error.kp_nametag_limit_reached",
        undefined,
        SLOW_WAIT,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("kp.nametags.unsaved")).toBeInTheDocument();
  });

  it("reports a failed load", async () => {
    server.use(
      http.get(nametagsUrl, () =>
        HttpResponse.json({ code: "server.error" }, { status: 500 }),
      ),
    );
    renderCard();

    expect(
      await screen.findByText("kp.nametags.load_error", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
  });
});
