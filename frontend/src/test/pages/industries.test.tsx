import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse, type DefaultBodyType } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import type { IndustryResponse } from "../../orval/generated/fastAPI.schemas";
import Industries from "../../pages/admin/Industries";
import { testBackendUrl } from "../constants";
import { softwareIndustry } from "../fixtures/admin";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { server } from "../server";

let catalogue: IndustryResponse[] = [];
let createdNames: unknown[] = [];
let renamed: { industryId: string; body: unknown }[] = [];
let deletedIds: string[] = [];
let createResponse: () => HttpResponse<DefaultBodyType>;

beforeEach(() => {
  catalogue = [softwareIndustry];
  createdNames = [];
  renamed = [];
  deletedIds = [];
  createResponse = () =>
    HttpResponse.json({ id: "new-industry", name: "Robotics" });
  localStorage.setItem("token", createToken(3600));

  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/industries`, () =>
      HttpResponse.json(catalogue),
    ),
    http.post(`${testBackendUrl}/api/industries`, async ({ request }) => {
      createdNames.push(await request.json());
      return createResponse();
    }),
    http.patch(
      `${testBackendUrl}/api/industries/:industryId`,
      async ({ params, request }) => {
        renamed.push({
          industryId: String(params.industryId),
          body: await request.json(),
        });
        return HttpResponse.json({
          id: params.industryId,
          name: "Software Engineering",
        });
      },
    ),
    http.delete(
      `${testBackendUrl}/api/industries/:industryId`,
      ({ params }) => {
        deletedIds.push(String(params.industryId));
        return new HttpResponse(null, { status: 204 });
      },
    ),
  );
});

const industryRow = async () => {
  const cell = await screen.findByText(softwareIndustry.name);
  const row = cell.closest("tr");
  if (!row) throw new Error("row not found");
  return within(row);
};

describe("the industry catalogue page", () => {
  it("lists the catalogue entries", async () => {
    renderWithProviders(<Industries />);

    expect(await screen.findByText(softwareIndustry.name)).toBeInTheDocument();
  });

  it("adds an industry", async () => {
    const { user } = renderWithProviders(<Industries />);
    await industryRow();

    await user.click(screen.getByRole("button", { name: "industries.add" }));
    await user.type(
      await screen.findByLabelText("industries.name"),
      "Robotics",
    );
    await user.click(
      within(await screen.findByRole("dialog")).getByRole("button", {
        name: "industries.add",
      }),
    );

    await waitFor(() => {
      expect(createdNames).toEqual([{ name: "Robotics" }]);
    });
  });

  it("renames an industry", async () => {
    const { user } = renderWithProviders(<Industries />);
    const row = await industryRow();

    await user.click(row.getByRole("button", { name: "industries.rename" }));
    const input = row.getByLabelText("industries.rename");
    await user.clear(input);
    await user.type(input, "Software Engineering");
    await user.click(
      row.getByRole("button", { name: "industries.rename_save" }),
    );

    await waitFor(() => {
      expect(renamed).toEqual([
        {
          industryId: softwareIndustry.id,
          body: { name: "Software Engineering" },
        },
      ]);
    });
  });

  it("deletes an industry after confirming the usage hint", async () => {
    const { user } = renderWithProviders(<Industries />);
    const row = await industryRow();

    await user.click(row.getByRole("button", { name: "industries.delete" }));
    expect(
      await screen.findByText("industries.delete_modal.usage_hint"),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "industries.delete_modal.confirm" }),
    );

    await waitFor(() => {
      expect(deletedIds).toEqual([softwareIndustry.id]);
    });
  });

  it("shows the conflict text when the name already exists", async () => {
    createResponse = () =>
      HttpResponse.json(
        {
          statusCode: 409,
          code: "error.industry_name_exists",
          identifier: "industry",
          message: "name exists",
        },
        { status: 409 },
      );
    const { user } = renderWithProviders(<Industries />);
    await industryRow();

    await user.click(screen.getByRole("button", { name: "industries.add" }));
    await user.type(
      await screen.findByLabelText("industries.name"),
      softwareIndustry.name,
    );
    await user.click(
      within(await screen.findByRole("dialog")).getByRole("button", {
        name: "industries.add",
      }),
    );

    expect(
      await screen.findByText("error.industry_name_exists"),
    ).toBeInTheDocument();
  });
});
