import { screen, waitFor } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ExportsTab from "../../components/kp-manage/ExportsTab";
import * as download from "../../utils/download";
import { testBackendUrl } from "../constants";
import { testEventId } from "../fixtures/kp-booking";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { server } from "../server";

const exportUrl = (name: string) =>
  `${testBackendUrl}/api/kp/events/:eventId/exports/${name}/download`;

const rejections: unknown[] = [];
const onRejection = (reason: unknown) => {
  rejections.push(reason);
};

beforeEach(() => {
  rejections.length = 0;
  process.on("unhandledRejection", onRejection);
  vi.spyOn(download, "downloadBlob").mockImplementation(() => undefined);
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/exports/nametags/background`,
      () => HttpResponse.json(null),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/exports/nametags/targets`,
      () => HttpResponse.json({ companies: [], people: [] }),
    ),
  );
});

afterEach(() => {
  process.off("unhandledRejection", onRejection);
});

const renderExports = (eventName = "KP 2026") =>
  renderWithProviders(
    <ExportsTab eventId={testEventId} eventName={eventName} />,
  );

const downloadButton = (name: string) =>
  screen.getByRole("button", {
    name: `kp.dashboard.exports.downloads.${name}`,
  });

describe("the data downloads", () => {
  it("handles a failing download", async () => {
    server.use(
      http.get(exportUrl("bookings"), () =>
        HttpResponse.json({ statusCode: 500 }, { status: 500 }),
      ),
    );
    const { user } = renderExports();

    await user.click(downloadButton("bookings"));

    await waitFor(() => expect(downloadButton("bookings")).toBeEnabled());
    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(rejections).toHaveLength(0);
    expect(download.downloadBlob).not.toHaveBeenCalled();
  });

  it("keeps a running download busy while another one finishes", async () => {
    server.use(
      http.get(exportUrl("bookings"), async () => {
        await delay(1000);
        return new HttpResponse(new Blob(["csv"]));
      }),
      http.get(
        exportUrl("waitlist-companies"),
        () => new HttpResponse(new Blob(["csv"])),
      ),
    );
    const { user } = renderExports();

    await user.click(downloadButton("bookings"));
    await user.click(downloadButton("waitlist"));

    await waitFor(() => expect(download.downloadBlob).toHaveBeenCalledTimes(1));
    expect(downloadButton("bookings")).toBeDisabled();
    await waitFor(() => expect(download.downloadBlob).toHaveBeenCalledTimes(2));
  });

  it("keeps umlauts readable in the file name", async () => {
    server.use(
      http.get(
        exportUrl("bookings"),
        () => new HttpResponse(new Blob(["csv"])),
      ),
    );
    const { user } = renderExports("Kontaktparty Zürich");

    await user.click(downloadButton("bookings"));

    await waitFor(() =>
      expect(download.downloadBlob).toHaveBeenCalledWith(
        expect.anything(),
        "kontaktparty-zurich-bookings-all.csv",
      ),
    );
  });
});
