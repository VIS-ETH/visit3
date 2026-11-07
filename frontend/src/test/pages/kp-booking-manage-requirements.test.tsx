import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingManage from "../../pages/KpBookingManage";
import type { KpResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  testBooking,
  testBookingId,
  testBookingServiceId,
  testEvent,
  testEventId,
  testFileRequirementId,
  testOpenEvent,
  testTextRequirementId,
} from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const managePath = "/kp/:id/booking/:bookingId/manage/services";
const manageRoute = `/kp/${testEventId}/booking/${testBookingId}/manage/services`;
const requirementsUrl = `${testBackendUrl}/api/kp/booking-services/${testBookingServiceId}/requirements`;
const textUrl = `${requirementsUrl}/${testTextRequirementId}/text`;
const fileUrl = `${requirementsUrl}/${testFileRequirementId}/file`;

let textPuts = 0;
let textGets = 0;
let savedText: string | null = null;

const serveEvent = (event: KpResponse) =>
  server.use(
    http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
      HttpResponse.json(event),
    ),
  );

const textAnswer = () =>
  savedText === null
    ? null
    : {
        id: "answer-1",
        booking_service_id: testBookingServiceId,
        requirement_id: testTextRequirementId,
        text_value: savedText,
      };

beforeEach(() => {
  textPuts = 0;
  textGets = 0;
  savedText = null;
  localStorage.setItem("token", createToken(3600));
  serveEvent(testOpenEvent);
  server.use(
    http.get(`${testBackendUrl}/api/kp/events/:eventId/my-booking`, () =>
      HttpResponse.json(testBooking),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/services/available`,
      () => HttpResponse.json([]),
    ),
    http.get(fileUrl, () => HttpResponse.json(null)),
    http.get(textUrl, async () => {
      textGets += 1;
      if (textGets > 1) await delay(800);
      return HttpResponse.json(textAnswer());
    }),
    http.put(textUrl, async ({ request }) => {
      textPuts += 1;
      savedText = ((await request.json()) as { text_value: string }).text_value;
      return HttpResponse.json(textAnswer());
    }),
  );
});

const renderManage = () =>
  renderWithProviders(
    <Routes>
      <Route path={managePath} element={<KpBookingManage />} />
    </Routes>,
    { route: manageRoute },
  );

const findTextarea = () =>
  screen.findByPlaceholderText(
    "kp.booking_manage.text_placeholder",
    undefined,
    SLOW_WAIT,
  );

describe("the requirements on the manage page", () => {
  it("locks services and requirements after the finalization deadline", async () => {
    serveEvent(testEvent);
    renderManage();

    expect(await findTextarea()).toBeDisabled();
    expect(
      screen.getByText("kp.booking_manage.deadline_notice"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "kp.booking_manage.add_services_submit",
      }),
    ).toBeDisabled();
    expect(
      screen.queryByRole("button", {
        name: "kp.booking_manage.save_requirement_changes",
      }),
    ).not.toBeInTheDocument();
  });

  it("warns before unload while requirement changes are unsaved", async () => {
    const { user } = renderManage();

    await user.type(await findTextarea(), "Hi");
    await screen.findByText("kp.booking_manage.pending_change");
    const unload = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(unload);

    expect(unload.defaultPrevented).toBe(true);
  });

  it("saves a change once even when confirmed again during the refetch", async () => {
    const { user } = renderManage();

    await user.type(await findTextarea(), "Hi");
    await user.click(
      screen.getByRole("button", {
        name: "kp.booking_manage.save_requirement_changes",
      }),
    );
    const submit = await screen.findByRole(
      "button",
      { name: "kp.booking_manage.confirm_requirement_changes_submit" },
      SLOW_WAIT,
    );
    fireEvent.click(submit);
    fireEvent.click(submit);
    await waitFor(() => expect(textPuts).toBe(1));
    fireEvent.click(submit);

    await waitFor(() => expect(textGets).toBe(2));
    await waitFor(() => expect(submit).not.toBeInTheDocument(), SLOW_WAIT);
    expect(textPuts).toBe(1);
  });

  it("removes a saved answer that was cleared", async () => {
    savedText = "Old slogan";
    let deletes = 0;
    server.use(
      http.delete(textUrl, () => {
        deletes += 1;
        savedText = null;
        return new HttpResponse(null, { status: 200 });
      }),
    );
    const { user } = renderManage();

    const textarea = await screen.findByDisplayValue(
      "Old slogan",
      undefined,
      SLOW_WAIT,
    );
    await user.clear(textarea);
    await user.click(
      screen.getByRole("button", {
        name: "kp.booking_manage.save_requirement_changes",
      }),
    );
    await user.click(
      await screen.findByRole(
        "button",
        { name: "kp.booking_manage.confirm_requirement_changes_submit" },
        SLOW_WAIT,
      ),
    );

    await waitFor(() => expect(deletes).toBe(1), SLOW_WAIT);
    expect(textPuts).toBe(0);
  });

  it("handles a failing download link without an unhandled rejection", async () => {
    server.use(
      http.get(fileUrl, () =>
        HttpResponse.json({
          id: "file-1",
          booking_service_id: testBookingServiceId,
          requirement_id: testFileRequirementId,
          stored_file: { id: "stored-1", original_filename: "brochure.pdf" },
        }),
      ),
      http.get(`${fileUrl}/download`, () =>
        HttpResponse.json({ code: "server.error" }, { status: 500 }),
      ),
    );
    const rejections: unknown[] = [];
    const onRejection = (reason: unknown) => rejections.push(reason);
    process.on("unhandledRejection", onRejection);
    const { user } = renderManage();

    const download = await screen.findByRole(
      "button",
      { name: "kp.booking_manage.download_file" },
      SLOW_WAIT,
    );
    await user.click(download);
    await waitFor(() => expect(download).not.toHaveAttribute("data-loading"));
    await new Promise((resolve) => setTimeout(resolve, 100));
    process.off("unhandledRejection", onRejection);

    expect(rejections).toHaveLength(0);
  });
});
