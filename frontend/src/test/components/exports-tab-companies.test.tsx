import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ExportsTab from "../../components/ExportsTab";
import * as download from "../../utils/download";
import { testBackendUrl } from "../constants";
import { testEventId } from "../fixtures/kp-booking";
import i18n from "../i18n";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { server } from "../server";

let workbookRequests: URL[] = [];

beforeEach(() => {
  workbookRequests = [];
  vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-09-26T10:00:00") });
  vi.spyOn(download, "downloadBlob").mockImplementation(() => undefined);
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/exports/nametags/background`,
      () => HttpResponse.json(null),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/exports/nametags/targets`,
      () => HttpResponse.json({ companies: [], people: [] }),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/exports/companies/download`,
      ({ request }) => {
        workbookRequests.push(new URL(request.url));
        return new HttpResponse(new Blob(["xlsx"]));
      },
    ),
  );
});

afterEach(async () => {
  vi.useRealTimers();
  await i18n.changeLanguage("en");
});

const renderExports = () =>
  renderWithProviders(<ExportsTab eventId={testEventId} eventName="KP 2026" />);

describe("the company workbook export", () => {
  it("replaces the company details and contacts files", () => {
    renderExports();

    expect(
      screen.getByRole("button", {
        name: "kp.dashboard.exports.downloads.companies",
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "kp.dashboard.exports.downloads.company_details",
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "kp.dashboard.exports.downloads.contacts",
      }),
    ).not.toBeInTheDocument();
  });

  it.each([
    ["en", "kp-2026-companies-2026-09-26.xlsx"],
    ["de", "kp-2026-unternehmen-2026-09-26.xlsx"],
  ])(
    "downloads the workbook in the %s staff language",
    async (language, filename) => {
      await i18n.changeLanguage(language);
      const { user } = renderExports();

      await user.click(
        screen.getByRole("button", {
          name: "kp.dashboard.exports.downloads.companies",
        }),
      );

      await waitFor(() =>
        expect(download.downloadBlob).toHaveBeenCalledWith(
          expect.anything(),
          filename,
        ),
      );
      expect(workbookRequests.at(-1)?.searchParams.get("language")).toBe(
        language,
      );
    },
  );
});
