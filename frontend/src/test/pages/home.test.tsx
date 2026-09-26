import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import Home from "../../pages/Home";
import { UserContext } from "../../context/useCurrentUser";
import { renderWithProviders } from "../render";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import type {
  EventBannerResponse,
  KpLatestResponse,
} from "../../orval/generated/fastAPI.schemas";
import banner800 from "../../assets/home/kontaktparty-banner-800.webp";
import banner1200 from "../../assets/home/kontaktparty-banner-1200.webp";
import banner2000 from "../../assets/home/kontaktparty-banner-2000.webp";

const latestEvent: KpLatestResponse = {
  id: "event-1",
  name: "Kontaktparty 2028",
  registration_open: "2028-09-01",
  registration_end: "2028-09-20",
  finalization_deadline: "2028-09-25",
  nametags_deadline: "2028-09-26",
  event_date: "2028-10-20",
  vat_rate_percent: 8.1,
  terms_url: null,
  finalization_reminder_days: 3,
  max_nametags_per_booking: 4,
  banner: null,
};

const customBanner: EventBannerResponse = {
  width: 2000,
  height: 700,
  sources: [
    { width: 800, url: "https://files.test/banner/800.webp" },
    { width: 1200, url: "https://files.test/banner/1200.webp" },
    { width: 2000, url: "https://files.test/banner/2000.webp" },
  ],
};

let latest: KpLatestResponse | null = latestEvent;

beforeEach(() => {
  latest = latestEvent;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/latest`, () =>
      HttpResponse.json(latest),
    ),
  );
});

const renderHome = () =>
  renderWithProviders(
    <UserContext.Provider value={{ user: undefined, isLoading: false }}>
      <Home />
    </UserContext.Provider>,
  );

const banner = () => screen.getByRole("img", { name: "home.kp.image_alt" });

const bannerShows = (source: string) =>
  waitFor(() => expect(banner()).toHaveAttribute("src", source));

describe("Home", () => {
  it("shows the bundled Kontaktparty banner in every width", async () => {
    renderHome();

    await bannerShows(banner1200);
    expect(banner().getAttribute("srcset")).toBe(
      `${banner800} 800w, ${banner1200} 1200w, ${banner2000} 2000w`,
    );
    expect(banner().getAttribute("sizes")).toBeTruthy();
  });

  it("reserves the banner's own aspect ratio", async () => {
    renderHome();

    await bannerShows(banner1200);
    expect(banner().getAttribute("width")).toBe("2000");
    expect(banner().getAttribute("height")).toBe("626");
  });

  it("shows the latest event's own banner in its real proportions", async () => {
    latest = { ...latestEvent, banner: customBanner };
    renderHome();

    await bannerShows("https://files.test/banner/1200.webp");
    expect(banner().getAttribute("srcset")).toBe(
      "https://files.test/banner/800.webp 800w, https://files.test/banner/1200.webp 1200w, https://files.test/banner/2000.webp 2000w",
    );
    expect(banner().getAttribute("width")).toBe("2000");
    expect(banner().getAttribute("height")).toBe("700");
  });

  it("falls back to the bundled banner without an event", async () => {
    latest = null;
    renderHome();

    await bannerShows(banner1200);
  });
});
