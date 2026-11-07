import { File as NodeFile } from "node:buffer";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpServiceForm from "../../pages/KpServiceForm";
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

const servicesUrl = `${testBackendUrl}/api/kp/events/${testEventId}/services`;

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

let created: Record<string, unknown>[] = [];
let updates = 0;
let uploads = 0;

const renderNewService = () =>
  renderWithProviders(
    <Routes>
      <Route path="/kp/:id/services/new" element={<KpServiceForm />} />
      <Route path="/kp/:id" element={<div data-testid="services-list" />} />
    </Routes>,
    { route: `/kp/${testEventId}/services/new` },
  );

const typeName = async (user: ReturnType<typeof renderNewService>["user"]) =>
  user.type(
    await screen.findByLabelText(
      "kp.manage.service_name",
      undefined,
      SLOW_WAIT,
    ),
    "Table",
  );

const saveButton = () => screen.getByRole("button", { name: "kp.manage.save" });

beforeEach(() => {
  created = [];
  updates = 0;
  uploads = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(servicesUrl, () => HttpResponse.json([chair])),
    http.post(servicesUrl, async ({ request }) => {
      created.push((await request.json()) as Record<string, unknown>);
      return HttpResponse.json({ ...chair, id: `new-${created.length}` });
    }),
    http.patch(`${testBackendUrl}/api/kp/services/:serviceId`, ({ params }) => {
      updates += 1;
      return HttpResponse.json({ ...chair, id: String(params.serviceId) });
    }),
  );
});

describe("saving the service form", () => {
  it("keeps save disabled until the service list reloaded", async () => {
    let listRequests = 0;
    server.use(
      http.get(servicesUrl, async () => {
        listRequests += 1;
        if (listRequests > 1) await delay(1500);
        return HttpResponse.json([chair]);
      }),
    );
    const { user } = renderNewService();

    await typeName(user);
    const save = saveButton();
    await user.click(save);
    await waitFor(() => expect(listRequests).toBe(2));

    expect(save).toBeDisabled();
    expect(
      await screen.findByTestId("services-list", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(created).toHaveLength(1);
  });

  it("updates the created service when saving again after the image upload failed", async () => {
    server.use(
      http.post(`${testBackendUrl}/api/kp/services/:serviceId/image`, () => {
        uploads += 1;
        return HttpResponse.json({ code: "x" }, { status: 500 });
      }),
    );
    const { user, container } = renderNewService();

    await typeName(user);
    await user.upload(
      container.querySelector<HTMLInputElement>('input[type="file"]')!,
      new NodeFile(["png"], "a.png", { type: "image/png" }) as unknown as File,
    );
    await user.click(saveButton());
    await waitFor(() => expect(uploads).toBe(1), SLOW_WAIT);
    await waitFor(() => expect(saveButton()).toBeEnabled());
    await user.click(saveButton());

    await waitFor(() => expect(uploads).toBe(2), SLOW_WAIT);
    expect(created).toHaveLength(1);
    expect(updates).toBe(1);
    expect(screen.queryByTestId("services-list")).not.toBeInTheDocument();
  });

  it("sends a whole number as the maximum per booking", async () => {
    const { user } = renderNewService();

    await typeName(user);
    const max = screen.getByLabelText("kp.manage.service_max_per_booking");
    await user.clear(max);
    await user.type(max, "2.5");
    await user.click(saveButton());

    await waitFor(() => expect(created).toHaveLength(1));
    expect(Number.isInteger(created[0].max_quantity_per_booking)).toBe(true);
  });

  it("shows a translated message when a number field is cleared", async () => {
    const { user } = renderNewService();

    await typeName(user);
    await user.clear(screen.getByLabelText("kp.manage.service_price"));
    await user.tab();

    expect(await screen.findByText("validation.required")).toBeInTheDocument();
    expect(screen.queryByText(/expected number/i)).not.toBeInTheDocument();
  });
});
