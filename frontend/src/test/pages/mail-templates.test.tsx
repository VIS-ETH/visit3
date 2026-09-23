import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse, type DefaultBodyType } from "msw";
import MailTemplates from "../../pages/MailTemplates";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  testDefaultMailTemplate,
  testMailPreview,
  testMailTemplate,
  testOtherMailTemplate,
  testOtherTemplateKey,
  testTemplateKey,
} from "../fixtures/mail-template";

let activeTemplate = testMailTemplate;

const templateByKey = (key: string) =>
  key === testOtherTemplateKey ? testOtherMailTemplate : activeTemplate;

const formatDate = (value: string) =>
  new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
    new Date(value),
  );

let updateBodies: unknown[] = [];
let testSendKeys: string[] = [];
let previewKeys: string[] = [];
let resetKeys: string[] = [];
let updateResponse: () => HttpResponse<DefaultBodyType>;

const invalidResponse = (details: Record<string, string>) => () =>
  HttpResponse.json(
    {
      statusCode: 400,
      code: "error.mail_template_invalid",
      identifier: `mail_template:${testTemplateKey}`,
      message: "Mail template is invalid",
      details,
    },
    { status: 400 },
  );

beforeEach(() => {
  updateBodies = [];
  testSendKeys = [];
  previewKeys = [];
  resetKeys = [];
  activeTemplate = testMailTemplate;
  updateResponse = () => HttpResponse.json(testMailTemplate);
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/mail-templates`, () =>
      HttpResponse.json([activeTemplate, testOtherMailTemplate]),
    ),
    http.get(`${testBackendUrl}/api/mail-templates/:key`, ({ params }) =>
      HttpResponse.json(templateByKey(String(params.key))),
    ),
    http.delete(`${testBackendUrl}/api/mail-templates/:key`, ({ params }) => {
      resetKeys.push(String(params.key));
      activeTemplate = testDefaultMailTemplate;
      return HttpResponse.json(testDefaultMailTemplate);
    }),
    http.put(
      `${testBackendUrl}/api/mail-templates/:key`,
      async ({ request }) => {
        updateBodies.push(await request.json());
        return updateResponse();
      },
    ),
    http.post(
      `${testBackendUrl}/api/mail-templates/:key/preview`,
      ({ params }) => {
        previewKeys.push(String(params.key));
        return HttpResponse.json(testMailPreview);
      },
    ),
    http.post(
      `${testBackendUrl}/api/mail-templates/:key/test-send`,
      ({ params }) => {
        testSendKeys.push(String(params.key));
        return HttpResponse.json(null);
      },
    ),
  );
});

const renderPage = () => renderWithProviders(<MailTemplates />);

const findSubject = () =>
  screen.findByLabelText("mail_templates.subject", {}, { timeout: 5000 });

describe("the mail templates page", () => {
  it("lists every template with its state and update date", async () => {
    renderPage();

    const customized = await screen.findByRole(
      "button",
      { name: new RegExp(testTemplateKey) },
      { timeout: 5000 },
    );
    expect(customized).toHaveTextContent("mail_templates.customized");
    expect(customized).toHaveTextContent(
      formatDate(String(testMailTemplate.updated_at)),
    );

    const untouched = screen.getByRole("button", {
      name: new RegExp(testOtherTemplateKey),
    });
    expect(untouched).toHaveTextContent("mail_templates.never_updated");
  });

  it("loads the template that is selected in the list", async () => {
    const { user } = renderPage();

    expect(await findSubject()).toHaveValue(testMailTemplate.subject_de);

    await user.click(
      screen.getByRole("button", { name: new RegExp(testOtherTemplateKey) }),
    );

    await waitFor(
      () => {
        expect(screen.getByLabelText("mail_templates.subject")).toHaveValue(
          testOtherMailTemplate.subject_de,
        );
      },
      { timeout: 5000 },
    );
  });

  it("inserts a variable at the cursor when its chip is clicked", async () => {
    const { user } = renderPage();

    await findSubject();
    const body = screen.getByLabelText("mail_templates.body");
    await user.clear(body);
    await user.type(body, "AB");
    await user.keyboard("{ArrowLeft}");

    await user.click(screen.getByRole("button", { name: "company_name" }));

    await waitFor(() => {
      expect(body).toHaveValue("A{{ company_name }}B");
    });
  });

  it("renders the preview html in a sandboxed iframe", async () => {
    renderPage();

    await findSubject();
    await waitFor(
      () => {
        expect(previewKeys).toContain(testTemplateKey);
      },
      { timeout: 5000 },
    );

    const frame = await screen.findByTitle(
      "mail_templates.preview_frame_title",
    );
    await waitFor(() => {
      expect(frame).toHaveAttribute("srcdoc", testMailPreview.html);
    });
    expect(frame).toHaveAttribute("sandbox", "");
    expect(screen.getByText(testMailPreview.text)).toBeInTheDocument();
  });

  it("saves the edited template", async () => {
    const { user } = renderPage();

    const subject = await findSubject();
    await user.clear(subject);
    await user.type(subject, "Neuer Betreff");
    await user.click(
      screen.getByRole("button", { name: "mail_templates.save" }),
    );

    await waitFor(() => {
      expect(updateBodies).toHaveLength(1);
    });
    expect(updateBodies[0]).toEqual({
      subject_de: "Neuer Betreff",
      subject_en: testMailTemplate.subject_en,
      body_de: testMailTemplate.body_de,
      body_en: testMailTemplate.body_en,
    });
  });

  it("shows the rejected placeholder on the field named in the details", async () => {
    updateResponse = invalidResponse({ field: "body_de", variable: "boss" });
    const { user } = renderPage();

    const body = await findSubject().then(() =>
      screen.getByLabelText("mail_templates.body"),
    );
    await user.clear(body);
    await user.type(body, "Hallo boss");
    await user.click(
      screen.getByRole("button", { name: "mail_templates.save" }),
    );

    expect(
      await screen.findByText(
        "mail_templates.invalid_variable",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
  });

  it("switches to the language of the rejected field", async () => {
    updateResponse = invalidResponse({ field: "subject_en", variable: "boss" });
    const { user } = renderPage();

    await findSubject();
    await user.click(
      screen.getByRole("button", { name: "mail_templates.save" }),
    );

    await waitFor(
      () => {
        expect(
          screen.getByRole("tab", { name: "mail_templates.tab_en" }),
        ).toHaveAttribute("aria-selected", "true");
      },
      { timeout: 5000 },
    );
    expect(screen.getByLabelText("mail_templates.subject")).toHaveValue(
      testMailTemplate.subject_en,
    );
    expect(
      screen.getByText("mail_templates.invalid_variable"),
    ).toBeInTheDocument();
  });

  it("reports a broken field without a placeholder name", async () => {
    updateResponse = invalidResponse({ field: "body_de" });
    const { user } = renderPage();

    await findSubject();
    await user.click(
      screen.getByRole("button", { name: "mail_templates.save" }),
    );

    expect(
      await screen.findByText(
        "mail_templates.invalid_field",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
  });

  it("compares the current texts with the delivered defaults", async () => {
    const { user } = renderPage();

    await findSubject();
    expect(
      screen.queryByText(String(testMailTemplate.default_body_de)),
    ).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "mail_templates.defaults_show" }),
    );

    expect(
      await screen.findByText(String(testMailTemplate.default_subject_de)),
    ).toBeInTheDocument();
    expect(
      screen.getByText(String(testMailTemplate.default_body_de)),
    ).toBeInTheDocument();
    expect(
      screen.getByText("mail_templates.defaults_current"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("mail_templates.defaults_default"),
    ).toBeInTheDocument();
  });

  it("resets the template to its default after confirmation", async () => {
    const { user } = renderPage();

    await findSubject();
    await user.click(
      screen.getByRole("button", { name: "mail_templates.reset" }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "mail_templates.reset_modal.confirm",
      }),
    );

    await waitFor(
      () => {
        expect(resetKeys).toEqual([testTemplateKey]);
      },
      { timeout: 5000 },
    );

    await waitFor(
      () => {
        expect(screen.getByLabelText("mail_templates.subject")).toHaveValue(
          testDefaultMailTemplate.subject_de,
        );
      },
      { timeout: 5000 },
    );
    await waitFor(() => {
      expect(
        screen.queryByRole("button", { name: "mail_templates.reset" }),
      ).not.toBeInTheDocument();
    });
    expect(
      screen.getByRole("button", { name: new RegExp(testTemplateKey) }),
    ).toHaveTextContent("mail_templates.never_updated");
  });

  it("keeps the template when the reset is cancelled", async () => {
    const { user } = renderPage();

    await findSubject();
    await user.click(
      screen.getByRole("button", { name: "mail_templates.reset" }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "mail_templates.reset_modal.cancel",
      }),
    );

    expect(resetKeys).toEqual([]);
    expect(screen.getByLabelText("mail_templates.subject")).toHaveValue(
      testMailTemplate.subject_de,
    );
  });

  it("offers no reset for an untouched template", async () => {
    const { user } = renderPage();

    await findSubject();
    await user.click(
      screen.getByRole("button", { name: new RegExp(testOtherTemplateKey) }),
    );

    await waitFor(
      () => {
        expect(screen.getByLabelText("mail_templates.subject")).toHaveValue(
          testOtherMailTemplate.subject_de,
        );
      },
      { timeout: 5000 },
    );
    expect(
      screen.queryByRole("button", { name: "mail_templates.reset" }),
    ).not.toBeInTheDocument();
  });

  it("asks the backend for a test mail", async () => {
    const { user } = renderPage();

    await findSubject();
    await user.click(
      screen.getByRole("button", { name: "mail_templates.test_send" }),
    );

    await waitFor(() => {
      expect(testSendKeys).toEqual([testTemplateKey]);
    });
  });
});
