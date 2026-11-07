import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import ServicesTab from "../../components/kp-manage/ServicesTab";
import {
  KpServiceCategory,
  type ServiceResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const servicesUrl = `${testBackendUrl}/api/kp/events/:eventId/services`;

const chair: ServiceResponse = {
  id: "svc-1",
  event_id: testEventId,
  name: "Chair",
  description: "",
  image_url: null,
  confirmation_description: null,
  order: 1,
  price: 1500,
  max_quantity_per_booking: 6,
  max_total_quantity: 0,
  remaining_total_quantity: null,
  is_active: true,
  requirements: [],
  category: KpServiceCategory.SERVICE,
  unit_label: null,
};

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
});

describe("the services tab", () => {
  it("tells a failed load apart from an empty list", async () => {
    server.use(
      http.get(servicesUrl, () =>
        HttpResponse.json({ statusCode: 500 }, { status: 500 }),
      ),
    );
    renderWithProviders(<ServicesTab eventId={testEventId} />);

    expect(
      await screen.findByText("error.load_failed", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("kp.manage.services_group_services_empty"),
    ).not.toBeInTheDocument();
  });

  it("names the active switch of every service", async () => {
    server.use(http.get(servicesUrl, () => HttpResponse.json([chair])));
    renderWithProviders(<ServicesTab eventId={testEventId} />);

    expect(
      await screen.findByRole(
        "switch",
        { name: "kp.manage.service_active_toggle" },
        SLOW_WAIT,
      ),
    ).toBeChecked();
  });
});
