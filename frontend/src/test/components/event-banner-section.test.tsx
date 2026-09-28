import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { File as NodeFile } from "node:buffer";
import EventBannerSection from "../../components/kp/EventBannerSection";
import type { EventBannerResponse } from "../../orval/generated/fastAPI.schemas";
import banner1200 from "../../assets/home/kontaktparty-banner-1200.webp";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { SLOW_WAIT } from "../timeouts";

vi.mock("../../utils/uploads", () => ({ UPLOADS_AVAILABLE: true }));

const eventId = "event-1";
const bannerUrl = `${testBackendUrl}/api/kp/events/${eventId}/banner`;
const customSource = "https://files.test/banner/1200.webp";

const storedBanner: EventBannerResponse = {
  width: 2000,
  height: 500,
  sources: [
    { width: 800, url: "https://files.test/banner/800.webp" },
    { width: 1200, url: customSource },
    { width: 2000, url: "https://files.test/banner/2000.webp" },
  ],
};

let banner: EventBannerResponse | null = null;
let uploads: FormDataEntryValue[] = [];
let resets = 0;

beforeEach(() => {
  banner = null;
  uploads = [];
  resets = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(bannerUrl, () => HttpResponse.json(banner)),
    http.put(bannerUrl, async ({ request }) => {
      const file = (await request.formData()).get("file");
      if (file !== null) uploads.push(file);
      banner = storedBanner;
      return HttpResponse.json(banner);
    }),
    http.delete(bannerUrl, () => {
      resets += 1;
      banner = null;
      return HttpResponse.json(null);
    }),
  );
});

const renderSection = () =>
  renderWithProviders(<EventBannerSection eventId={eventId} />);

const fileInput = (container: HTMLElement) =>
  container.querySelector<HTMLInputElement>('input[type="file"]')!;

const imageFile = (size = 1024, name = "banner.png") =>
  new NodeFile([new Uint8Array(size)], name, {
    type: "image/png",
  }) as unknown as File;

const preview = () =>
  screen.getByRole("img", { name: "kp.dashboard.banner.preview_alt" });

const previewShows = (source: string) =>
  waitFor(() => expect(preview()).toHaveAttribute("src", source), SLOW_WAIT);

const resetButton = () =>
  screen.queryByRole("button", { name: "kp.dashboard.banner.reset" });

describe("the event banner section", () => {
  it("previews the default banner and offers no reset", async () => {
    renderSection();

    await previewShows(banner1200);
    expect(
      screen.getByText("kp.dashboard.banner.default_banner"),
    ).toBeInTheDocument();
    expect(resetButton()).not.toBeInTheDocument();
  });

  it("previews the uploaded banner in its own proportions", async () => {
    banner = storedBanner;
    renderSection();

    await previewShows(customSource);
    expect(preview()).toHaveAttribute("width", "2000");
    expect(preview()).toHaveAttribute("height", "500");
    expect(resetButton()).toBeInTheDocument();
  });

  it("uploads an image and shows it", async () => {
    const { user, container } = renderSection();
    await previewShows(banner1200);

    await user.upload(fileInput(container), imageFile());

    await waitFor(() => expect(uploads).toHaveLength(1), SLOW_WAIT);
    await previewShows(customSource);
  });

  it("refuses a file above the upload limit before sending it", async () => {
    const { user, container } = renderSection();
    await previewShows(banner1200);

    await user.upload(fileInput(container), imageFile(6 * 1024 * 1024));

    expect(
      await screen.findByText("kp.dashboard.banner.file_too_large"),
    ).toBeInTheDocument();
    expect(uploads).toHaveLength(0);
  });

  it("resets to the default only after confirming", async () => {
    banner = storedBanner;
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const { user } = renderSection();
    await previewShows(customSource);

    await user.click(resetButton()!);
    expect(resets).toBe(0);

    confirmSpy.mockReturnValue(true);
    await user.click(resetButton()!);

    await waitFor(() => expect(resets).toBe(1));
    await previewShows(banner1200);
    expect(resetButton()).not.toBeInTheDocument();
  });
});
