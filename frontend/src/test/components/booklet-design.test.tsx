import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { File as NodeFile } from "node:buffer";
import ExportsTab from "../../components/ExportsTab";
import BookletDesignSection from "../../components/kp/BookletDesignSection";
import type {
  BookletBackgroundResponse,
  UserResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { SLOW_WAIT } from "../timeouts";

const eventId = "event-1";
const backgroundUrl = `${testBackendUrl}/api/kp/events/${eventId}/booklet/background`;
const previewUrl = `${testBackendUrl}/api/kp/events/${eventId}/booklet/preview`;
const PNG_BASE64 = "iVBORw0KGgo=";

const storedBackground: BookletBackgroundResponse = {
  filename: "vis-booklet.pdf",
  size_bytes: 42_000,
  download_url: "https://files.test/vis-booklet.pdf",
};

let background: BookletBackgroundResponse | null = null;
let uploads: FormDataEntryValue[] = [];
let resets = 0;
let previews = 0;

beforeEach(() => {
  background = null;
  uploads = [];
  resets = 0;
  previews = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(backgroundUrl, () => HttpResponse.json(background)),
    http.put(backgroundUrl, async ({ request }) => {
      const file = (await request.formData()).get("file");
      if (file !== null) uploads.push(file);
      background = storedBackground;
      return HttpResponse.json(background);
    }),
    http.delete(backgroundUrl, () => {
      resets += 1;
      background = null;
      return HttpResponse.json(null);
    }),
    http.post(previewUrl, () => {
      previews += 1;
      return HttpResponse.json({ png_base64: PNG_BASE64, overflow: false });
    }),
  );
});

const renderSection = () =>
  renderWithProviders(<BookletDesignSection eventId={eventId} />);

const fileInput = (container: HTMLElement) =>
  container.querySelector<HTMLInputElement>('input[type="file"]')!;

const pdfFile = (size = 1024, name = "design.pdf") =>
  new NodeFile([new Uint8Array(size)], name, {
    type: "application/pdf",
  }) as unknown as File;

describe("the booklet design section", () => {
  it("shows the built-in design with a preview and no download", async () => {
    renderSection();

    expect(
      await screen.findByText("kp.dashboard.booklet.default_design"),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("img", {
        name: "kp.dashboard.booklet.preview_alt",
      }),
    ).toHaveAttribute("src", `data:image/png;base64,${PNG_BASE64}`);
    expect(
      screen.queryByRole("link", { name: /kp\.dashboard\.booklet\.download/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.dashboard.booklet.reset" }),
    ).not.toBeInTheDocument();
  });

  it("offers the stored background for download", async () => {
    background = storedBackground;
    renderSection();

    expect(
      await screen.findByRole("link", {
        name: /kp\.dashboard\.booklet\.download/,
      }),
    ).toHaveAttribute("href", storedBackground.download_url);
    expect(screen.getByText(storedBackground.filename)).toBeInTheDocument();
  });

  it("uploads a PDF and renders the preview again", async () => {
    const { user, container } = renderSection();
    await screen.findByRole("img", {
      name: "kp.dashboard.booklet.preview_alt",
    });
    const previewsBefore = previews;

    await user.upload(fileInput(container), pdfFile());

    await waitFor(() => expect(uploads).toHaveLength(1), SLOW_WAIT);
    expect(
      await screen.findByRole("link", {
        name: /kp\.dashboard\.booklet\.download/,
      }),
    ).toBeInTheDocument();
    await waitFor(() => expect(previews).toBeGreaterThan(previewsBefore));
  });

  it("refuses a file above the upload limit before sending it", async () => {
    const { user, container } = renderSection();
    await screen.findByText("kp.dashboard.booklet.default_design");

    await user.upload(fileInput(container), pdfFile(1024 * 1024));

    expect(
      await screen.findByText("kp.dashboard.booklet.file_too_large"),
    ).toBeInTheDocument();
    expect(uploads).toHaveLength(0);
  });

  it("resets to the built-in design only after confirming", async () => {
    background = storedBackground;
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const { user } = renderSection();
    const reset = await screen.findByRole("button", {
      name: "kp.dashboard.booklet.reset",
    });

    await user.click(reset);
    expect(resets).toBe(0);

    confirmSpy.mockReturnValue(true);
    await user.click(reset);

    await waitFor(() => expect(resets).toBe(1));
    expect(
      await screen.findByText("kp.dashboard.booklet.default_design"),
    ).toBeInTheDocument();
  });
});

describe("the exports tab", () => {
  const staffUser: UserResponse = {
    id: "staff-1",
    email: "staff@vis.ethz.ch",
    is_staff: true,
    is_admin: false,
    is_company: false,
    is_kp_president: true,
    user_confirmed: true,
    email_confirmed: true,
    company_id: null,
  };

  const renderExports = (user: UserResponse) =>
    renderWithProviders(
      <ExportsTab
        eventId={eventId}
        eventName="KP"
        canManageBooklet={user.is_admin}
      />,
    );

  it("shows the booklet design to admins", async () => {
    renderExports({ ...staffUser, is_admin: true });

    expect(
      await screen.findByText("kp.dashboard.booklet.title"),
    ).toBeInTheDocument();
  });

  it("hides the booklet design from other staff", async () => {
    renderExports(staffUser);

    await screen.findByText("kp.dashboard.exports.title");
    expect(
      screen.queryByText("kp.dashboard.booklet.title"),
    ).not.toBeInTheDocument();
  });
});
