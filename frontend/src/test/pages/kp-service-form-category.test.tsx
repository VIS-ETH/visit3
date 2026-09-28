import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpServiceForm from "../../pages/KpServiceForm";
import ServicesTab from "../../components/ServicesTab";
import { KpServiceCategory } from "../../orval/generated/fastAPI.schemas";
import type { ServiceResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const servicesUrl = `${testBackendUrl}/api/kp/events/${testEventId}/services`;

const serviceDefaults = {
  event_id: testEventId,
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
};

const powerSocket: ServiceResponse = {
  ...serviceDefaults,
  id: "service-power",
  name: "Power Socket",
  category: KpServiceCategory.SERVICE,
  unit_label: null,
};

const chair: ServiceResponse = {
  ...serviceDefaults,
  id: "booth-chair",
  name: "Stuhl",
  category: KpServiceCategory.BOOTH_ELEMENT,
  unit_label: "Stück",
};

let createdPayload: unknown = null;

const renderForm = () =>
  renderWithProviders(
    <Routes>
      <Route path="/kp/:id/services/new" element={<KpServiceForm />} />
    </Routes>,
    { route: `/kp/${testEventId}/services/new` },
  );

beforeEach(() => {
  createdPayload = null;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(servicesUrl, () => HttpResponse.json([powerSocket, chair])),
    http.post(servicesUrl, async ({ request }) => {
      createdPayload = await request.json();
      return HttpResponse.json(chair);
    }),
  );
});

describe("the admin service form", () => {
  it("sends the chosen category and unit label", async () => {
    const { user } = renderForm();

    await user.type(
      await screen.findByLabelText(
        "kp.manage.service_name",
        undefined,
        SLOW_WAIT,
      ),
      "Stehtisch",
    );
    await user.click(
      screen.getByRole("radio", {
        name: "kp.manage.service_category_booth_element",
      }),
    );
    await user.type(
      screen.getByLabelText("kp.manage.service_unit_label"),
      "Stück",
    );
    await user.click(screen.getByRole("button", { name: "kp.manage.save" }));

    await waitFor(() => {
      expect(createdPayload).toMatchObject({
        name: "Stehtisch",
        category: KpServiceCategory.BOOTH_ELEMENT,
        unit_label: "Stück",
      });
    }, SLOW_WAIT);
  });

  it("defaults a new service to the service category", async () => {
    const { user } = renderForm();

    await user.type(
      await screen.findByLabelText(
        "kp.manage.service_name",
        undefined,
        SLOW_WAIT,
      ),
      "Beamer",
    );
    await user.click(screen.getByRole("button", { name: "kp.manage.save" }));

    await waitFor(() => {
      expect(createdPayload).toMatchObject({
        category: KpServiceCategory.SERVICE,
        unit_label: null,
      });
    }, SLOW_WAIT);
  });
});

describe("the admin services tab", () => {
  it("lists services and booth elements in separate groups", async () => {
    renderWithProviders(<ServicesTab eventId={testEventId} />);

    await screen.findByText(powerSocket.name, undefined, SLOW_WAIT);

    const groups = screen.getAllByRole("table");
    expect(groups).toHaveLength(2);
    expect(
      screen.getByText("kp.manage.services_group_services"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.manage.services_group_booth_elements"),
    ).toBeInTheDocument();
    expect(groups[0]).toHaveTextContent(powerSocket.name);
    expect(groups[0]).not.toHaveTextContent(chair.name);
    expect(groups[1]).toHaveTextContent(chair.name);
  });
});
