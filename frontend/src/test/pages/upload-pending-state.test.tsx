import { File as NodeFile } from "node:buffer";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import ExportsTab from "../../components/ExportsTab";
import CompanyLogoField from "../../components/company/CompanyLogoField";
import KpBookingManage from "../../pages/KpBookingManage";
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
} from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const pdfFile = () =>
  new NodeFile(["%PDF-1.7"], "brochure.pdf", {
    type: "application/pdf",
  }) as unknown as File;

const pngFile = () =>
  new NodeFile(["png"], "background.png", {
    type: "image/png",
  }) as unknown as File;

const deferred = () => {
  let release: () => void = () => undefined;
  const released = new Promise<void>((resolve) => {
    release = resolve;
  });
  return { release, released };
};

const fileInput = (container: HTMLElement) =>
  container.querySelector<HTMLInputElement>('input[type="file"]');

const storedPdf = {
  id: "answer-1",
  booking_service_id: testBookingServiceId,
  requirement_id: testFileRequirementId,
  stored_file: {
    id: "stored-1",
    original_filename: "brochure.pdf",
    mime_type: "application/pdf",
    size_bytes: 8,
    sha256: "sha",
  },
};

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
  );
});

describe("a booking requirement file", () => {
  const manageRoute = `/kp/${testEventId}/booking/${testBookingId}/manage/services`;
  let storedFile: typeof storedPdf | null = null;

  beforeEach(() => {
    storedFile = null;
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
        () => HttpResponse.json(storedFile),
      ),
    );
  });

  const renderManage = () =>
    renderWithProviders(
      <Routes>
        <Route
          path="/kp/:id/booking/:bookingId/manage/services"
          element={<KpBookingManage />}
        />
      </Routes>,
      { route: manageRoute },
    );

  const pickAndSave = async (
    user: ReturnType<typeof renderManage>["user"],
    container: HTMLElement,
  ) => {
    await screen.findByText(
      "kp.booking_manage.incomplete_requirements_notice",
      undefined,
      SLOW_WAIT,
    );
    await user.upload(fileInput(container)!, pdfFile());
    expect(
      screen.getByText("kp.booking_manage.incomplete_requirements_notice"),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", {
        name: "kp.booking_manage.save_requirement_changes",
      }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "kp.booking_manage.confirm_requirement_changes_submit",
      }),
    );
  };

  it("counts only once the server stored it", async () => {
    const upload = deferred();
    server.use(
      http.post(
        `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/file`,
        async () => {
          await upload.released;
          storedFile = storedPdf;
          return HttpResponse.json(storedPdf);
        },
      ),
    );
    const { user, container } = renderManage();

    await pickAndSave(user, container);

    expect(
      await screen.findByText("kp.booking_manage.uploading"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /brochure\.pdf/ }),
    ).toBeDisabled();
    expect(
      screen.getByText("kp.booking_manage.incomplete_requirements_notice"),
    ).toBeInTheDocument();

    upload.release();

    await waitFor(() =>
      expect(
        screen.queryByText("kp.booking_manage.incomplete_requirements_notice"),
      ).not.toBeInTheDocument(),
    );
    expect(
      screen.queryByText("kp.booking_manage.uploading"),
    ).not.toBeInTheDocument();
  });

  it("clears the pending state when the upload fails", async () => {
    server.use(
      http.post(
        `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/file`,
        () =>
          HttpResponse.json(
            {
              statusCode: 400,
              code: "error.storage_file_too_large",
              message: "too large",
            },
            { status: 400 },
          ),
      ),
    );
    const { user, container } = renderManage();

    await pickAndSave(user, container);

    await waitFor(() =>
      expect(
        screen.queryByText("kp.booking_manage.uploading"),
      ).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: /brochure\.pdf/ })).toBeEnabled();
    expect(
      screen.getByText("kp.booking_manage.incomplete_requirements_notice"),
    ).toBeInTheDocument();
  });
});

describe("the nametag export background", () => {
  it("keeps the export waiting until the background is stored", async () => {
    const upload = deferred();
    let background: { id: string } | null = { id: "old-background" };
    server.use(
      http.get(
        `${testBackendUrl}/api/kp/events/:eventId/exports/nametags/background`,
        () => HttpResponse.json(background),
      ),
      http.get(
        `${testBackendUrl}/api/kp/events/:eventId/exports/nametags/targets`,
        () => HttpResponse.json({ companies: [], people: [] }),
      ),
      http.post(
        `${testBackendUrl}/api/kp/events/:eventId/exports/nametags/background`,
        async () => {
          await upload.released;
          background = { id: "new-background" };
          return HttpResponse.json(background);
        },
      ),
    );
    const { user, container } = renderWithProviders(
      <ExportsTab eventId={testEventId} eventName="KP" />,
    );
    const download = await screen.findByRole("button", {
      name: "kp.dashboard.exports.download_event_nametags",
    });
    await waitFor(() => expect(download).toBeEnabled());

    await user.upload(fileInput(container)!, pngFile());
    await user.click(
      screen.getByRole("button", {
        name: "kp.dashboard.exports.upload_background",
      }),
    );

    const picker = screen.getByLabelText("kp.dashboard.exports.background");
    await waitFor(() => expect(picker).toBeDisabled());
    expect(download).toBeDisabled();

    upload.release();

    await waitFor(() => expect(download).toBeEnabled());
    expect(picker).toBeEnabled();
  });
});

describe("the company logo", () => {
  it("shows the logo and warns before leaving only while it uploads", async () => {
    const upload = deferred();
    server.use(
      http.post(`${testBackendUrl}/api/company/me/profile/logo`, async () => {
        await upload.released;
        return HttpResponse.json({ logo_url: "https://storage.test/logo" });
      }),
      http.get(`${testBackendUrl}/api/company/me`, () =>
        HttpResponse.json({ id: "company-1", name: "Acme" }),
      ),
    );
    const { user, container } = renderWithProviders(
      <CompanyLogoField logoUrl={null} disabled={false} />,
    );

    await user.upload(
      fileInput(container)!,
      new NodeFile(["png"], "logo.png", {
        type: "image/png",
      }) as unknown as File,
    );

    const leaving = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(leaving);
    expect(leaving.defaultPrevented).toBe(true);
    expect(
      screen.queryByAltText("company_profile_form.logo_alt"),
    ).not.toBeInTheDocument();

    upload.release();

    await waitFor(() => {
      const afterUpload = new Event("beforeunload", { cancelable: true });
      window.dispatchEvent(afterUpload);
      expect(afterUpload.defaultPrevented).toBe(false);
    });
  });
});
