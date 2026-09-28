import { fireEvent, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import CompanyDescriptionEditor from "../../components/company/CompanyDescriptionEditor";
import { renderWithProviders } from "../render";

const Harness = ({
  initial,
  onChange,
}: {
  initial: string;
  onChange: (value: string) => void;
}) => {
  const [value, setValue] = useState(initial);
  return (
    <CompanyDescriptionEditor
      id="company-profile-description"
      label="company_profile_form.description"
      description="company_profile_form.description_counter"
      value={value}
      disabled={false}
      onChange={(next) => {
        setValue(next);
        onChange(next);
      }}
    />
  );
};

const renderEditor = (initial: string) => {
  const onChange = vi.fn();
  const view = renderWithProviders(
    <Harness initial={initial} onChange={onChange} />,
  );
  return { ...view, onChange };
};

const content = () =>
  screen.getByRole("textbox", { name: "company_profile_form.description" });

const lastValue = (onChange: ReturnType<typeof vi.fn>) =>
  onChange.mock.calls.at(-1)?.[0] as string | undefined;

describe("the company description editor", () => {
  it("offers exactly the four formatting controls", () => {
    renderEditor("<p>Hello</p>");

    expect(
      screen
        .getAllByRole("button")
        .map((button) => button.getAttribute("aria-label")),
    ).toEqual([
      "company_profile_form.editor_bold",
      "company_profile_form.editor_italic",
      "company_profile_form.editor_underline",
      "company_profile_form.editor_strike",
    ]);
  });

  it.each([
    ["company_profile_form.editor_bold", "<p><strong>Hello</strong></p>"],
    ["company_profile_form.editor_italic", "<p><em>Hello</em></p>"],
    ["company_profile_form.editor_underline", "<p><u>Hello</u></p>"],
    ["company_profile_form.editor_strike", "<p><s>Hello</s></p>"],
  ])("formats the selection with %s", async (control, expected) => {
    const { user, onChange } = renderEditor("<p>Hello</p>");

    await user.click(content());
    await user.keyboard("{Control>}a{/Control}");
    await user.click(screen.getByRole("button", { name: control }));

    await waitFor(() => expect(lastValue(onChange)).toBe(expected));
  });

  it("keeps only the allowed formatting when pasting", async () => {
    const { user, onChange } = renderEditor("<p></p>");

    await user.click(content());
    fireEvent.paste(content(), {
      clipboardData: {
        types: ["text/html", "text/plain"],
        getData: (type: string) =>
          type === "text/html"
            ? '<h1>Title</h1><p><strong>Bold</strong> <a href="https://x.test">link</a> <span style="color:red">red</span><img src="x"></p><ul><li>item</li></ul>'
            : "Title Bold link red item",
      },
    });

    await waitFor(() =>
      expect(lastValue(onChange)).toBe(
        "<p>Title</p><p><strong>Bold</strong> link red</p><p>item</p>",
      ),
    );
  });

  it("reports an emptied editor as an empty value", async () => {
    const { user, onChange } = renderEditor("<p>Hello</p>");

    await user.click(content());
    await user.keyboard("{Control>}a{/Control}{Backspace}");

    await waitFor(() => expect(lastValue(onChange)).toBe(""));
  });
});
