import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Button } from "@mantine/core";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import RepickableFileButton from "../../components/RepickableFileButton";
import UploadFileInput from "../../components/UploadFileInput";
import CompanyLogoField from "../../components/company/CompanyLogoField";
import KpBookingManage from "../../pages/KpBookingManage";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  testBooking,
  testBookingId,
  testEvent,
  testEventId,
} from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.hoisted(() => {
  const element = document.getElementById("server-data");
  if (element === null) throw new Error("server data missing");
  element.textContent = JSON.stringify({
    ...JSON.parse(element.textContent ?? "{}"),
    uploadsUnavailable: "true",
  });
});

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const NOTICE_TITLE = "uploads.unavailable_title";
const PICK = "test.pick_file";

let uploadRequests: string[] = [];
let openFileDialog: ReturnType<typeof vi.spyOn>;

const recordUpload = ({ request }: { request: Request }) => {
  uploadRequests.push(new URL(request.url).pathname);
  return HttpResponse.json({});
};

beforeEach(() => {
  uploadRequests = [];
  openFileDialog = vi.spyOn(HTMLInputElement.prototype, "click");
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.post(`${testBackendUrl}/api/*`, recordUpload),
    http.put(`${testBackendUrl}/api/*`, recordUpload),
  );
});

afterEach(() => {
  openFileDialog.mockRestore();
});

const expectNoticeInsteadOfUpload = async () => {
  expect(
    await screen.findByText(NOTICE_TITLE, undefined, SLOW_WAIT),
  ).toBeInTheDocument();
  expect(screen.getByText("uploads.unavailable_body")).toBeInTheDocument();
  expect(openFileDialog).not.toHaveBeenCalled();
  expect(uploadRequests).toEqual([]);
};

describe("uploads while they are unavailable", () => {
  it("shows the notice instead of the file dialog of a file button", async () => {
    const onChange = vi.fn();
    const { user } = renderWithProviders(
      <RepickableFileButton onChange={onChange}>
        {(props) => <Button {...props}>{PICK}</Button>}
      </RepickableFileButton>,
    );

    await user.click(screen.getByRole("button", { name: PICK }));

    await expectNoticeInsteadOfUpload();
    expect(onChange).not.toHaveBeenCalled();
    expect(document.querySelector('input[type="file"]')).toBeNull();
  });

  it("shows the notice instead of the file dialog of a file input", async () => {
    const onChange = vi.fn();
    const { user } = renderWithProviders(
      <UploadFileInput placeholder={PICK} onChange={onChange} />,
    );

    await user.click(screen.getByRole("button", { name: PICK }));

    await expectNoticeInsteadOfUpload();
    expect(onChange).not.toHaveBeenCalled();
  });

  it("closes the notice with its button", async () => {
    const { user } = renderWithProviders(
      <RepickableFileButton onChange={vi.fn()}>
        {(props) => <Button {...props}>{PICK}</Button>}
      </RepickableFileButton>,
    );

    await user.click(screen.getByRole("button", { name: PICK }));
    await user.click(
      await screen.findByRole("button", { name: "common.ok" }, SLOW_WAIT),
    );

    await waitFor(() =>
      expect(screen.queryByText(NOTICE_TITLE)).not.toBeInTheDocument(),
    );
  });

  it("keeps the company logo from uploading", async () => {
    const { user } = renderWithProviders(
      <CompanyLogoField logoUrl={null} disabled={false} />,
    );

    await user.click(
      screen.getByRole("button", { name: "company_profile_form.logo_upload" }),
    );

    await expectNoticeInsteadOfUpload();
  });

  it("keeps a booking requirement file from uploading", async () => {
    server.use(
      http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
        HttpResponse.json(testEvent),
      ),
      http.get(`${testBackendUrl}/api/kp/events/:eventId/my-booking`, () =>
        HttpResponse.json(testBooking),
      ),
      http.get(
        `${testBackendUrl}/api/kp/events/:eventId/services/available`,
        () => HttpResponse.json([]),
      ),
      http.get(
        `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/text`,
        () => HttpResponse.json({ text_value: "Our slogan" }),
      ),
      http.get(
        `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/file`,
        () => HttpResponse.json(null),
      ),
    );
    const { user } = renderWithProviders(
      <Routes>
        <Route
          path="/kp/:id/booking/:bookingId/manage/services"
          element={<KpBookingManage />}
        />
      </Routes>,
      {
        route: `/kp/${testEventId}/booking/${testBookingId}/manage/services`,
      },
    );

    await user.click(
      await screen.findByRole(
        "button",
        { name: /kp\.booking_manage\.upload_file/ },
        SLOW_WAIT,
      ),
    );

    await expectNoticeInsteadOfUpload();
  });
});
