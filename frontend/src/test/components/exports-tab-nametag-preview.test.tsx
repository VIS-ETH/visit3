import { File as NodeFile } from "node:buffer";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import ExportsTab from "../../components/kp-manage/ExportsTab";
import { testBackendUrl } from "../constants";
import { testEventId } from "../fixtures/kp-booking";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { server } from "../server";

const exportsUrl = `${testBackendUrl}/api/kp/events/:eventId/exports/nametags`;
const FIRST_PNG = "Zmlyc3Q=";
const SECOND_PNG = "c2Vjb25k";

let background: { id: string } | null = null;
let previews: string[] = [];
let previewPng = FIRST_PNG;

beforeEach(() => {
  background = null;
  previews = [];
  previewPng = FIRST_PNG;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${exportsUrl}/background`, () => HttpResponse.json(background)),
    http.post(`${exportsUrl}/background`, () => {
      background = { id: "new-background" };
      previewPng = SECOND_PNG;
      return HttpResponse.json(background);
    }),
    http.get(`${exportsUrl}/targets`, () =>
      HttpResponse.json({ companies: [], people: [] }),
    ),
    http.get(`${exportsUrl}/preview`, () => {
      previews.push(previewPng);
      return HttpResponse.json({ png_base64: previewPng });
    }),
  );
});

const renderExports = () =>
  renderWithProviders(<ExportsTab eventId={testEventId} eventName="KP" />);

const showPreviewButton = () =>
  screen.findByRole("button", { name: "kp.dashboard.exports.show_preview" });

const previewImage = () =>
  screen.findByRole("img", { name: "kp.dashboard.exports.preview_alt" });

describe("the nametag preview", () => {
  it("cannot be opened without a background", async () => {
    renderExports();

    await screen.findByText("kp.dashboard.exports.background_missing");
    expect(await showPreviewButton()).toBeDisabled();
    expect(previews).toHaveLength(0);
  });

  it("renders only when opened and refreshes after a new upload", async () => {
    background = { id: "old-background" };
    const { user, container } = renderExports();
    const button = await showPreviewButton();
    await waitFor(() => expect(button).toBeEnabled());
    expect(previews).toHaveLength(0);

    await user.click(button);

    expect(await previewImage()).toHaveAttribute(
      "src",
      `data:image/png;base64,${FIRST_PNG}`,
    );

    await user.upload(
      container.querySelector<HTMLInputElement>('input[type="file"]')!,
      new NodeFile(["png"], "background.png", {
        type: "image/png",
      }) as unknown as File,
    );
    await user.click(
      screen.getByRole("button", {
        name: "kp.dashboard.exports.upload_background",
      }),
    );

    await waitFor(async () =>
      expect(await previewImage()).toHaveAttribute(
        "src",
        `data:image/png;base64,${SECOND_PNG}`,
      ),
    );
    expect(previews).toEqual([FIRST_PNG, SECOND_PNG]);

    await user.click(
      screen.getByRole("button", { name: "kp.dashboard.exports.hide_preview" }),
    );
    expect(
      screen.queryByRole("img", { name: "kp.dashboard.exports.preview_alt" }),
    ).not.toBeInTheDocument();
  });
});
