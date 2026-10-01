import { fireEvent, screen, waitFor } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";
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

const control = (name: string) =>
  screen.getByRole("button", { name: `company_profile_form.${name}` });

const lastValue = (onChange: ReturnType<typeof vi.fn>) =>
  onChange.mock.calls.at(-1)?.[0] as string | undefined;

const paste = (data: Record<string, string>) => {
  fireEvent.paste(content(), {
    clipboardData: {
      types: Object.keys(data),
      getData: (type: string) => data[type] ?? "",
    },
  });
};

const KEY = /\{[^}]*\}|./gsu;

const write = async (user: UserEvent, keys: string) => {
  for (const key of keys.match(KEY) ?? []) {
    await user.keyboard(key);
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
};

const expectValue = async (
  onChange: ReturnType<typeof vi.fn>,
  expected: string,
) => {
  await waitFor(() => expect(lastValue(onChange)).toBe(expected));
};

describe("the company description editor", () => {
  it("offers formatting, list and history controls only", () => {
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
      "company_profile_form.editor_bullet_list",
      "company_profile_form.editor_ordered_list",
      "company_profile_form.editor_indent",
      "company_profile_form.editor_outdent",
      "company_profile_form.editor_undo",
      "company_profile_form.editor_redo",
    ]);
  });

  it("explains paragraphs, line breaks and lists below the editor", () => {
    renderEditor("<p>Hello</p>");

    expect(content()).toHaveAccessibleDescription(
      "company_profile_form.editor_hint",
    );
  });

  it.each([
    ["editor_bold", "<p><strong>Hello</strong></p>"],
    ["editor_italic", "<p><em>Hello</em></p>"],
    ["editor_underline", "<p><u>Hello</u></p>"],
    ["editor_strike", "<p><s>Hello</s></p>"],
    ["editor_bullet_list", "<ul><li><p>Hello</p></li></ul>"],
    ["editor_ordered_list", "<ol><li><p>Hello</p></li></ol>"],
  ])("formats the selection with %s", async (name, expected) => {
    const { user, onChange } = renderEditor("<p>Hello</p>");

    await user.click(content());
    await user.keyboard("{Control>}a{/Control}");
    await user.click(control(name));

    await expectValue(onChange, expected);
  });

  it("turns a list back into paragraphs", async () => {
    const { user, onChange } = renderEditor(
      "<ul><li><p>a</p></li><li><p>b</p></li></ul>",
    );

    await user.click(content());
    await user.keyboard("{Control>}a{/Control}");
    await user.click(control("editor_bullet_list"));

    await expectValue(onChange, "<p>a</p><p>b</p>");
  });

  it.each([
    ["- ", "<ul><li><p>Item</p></li></ul>"],
    ["* ", "<ul><li><p>Item</p></li></ul>"],
    ["1. ", "<ol><li><p>Item</p></li></ol>"],
    ["4. ", "<ol><li><p>Item</p></li></ol>"],
  ])("starts a list when typing %j", async (shortcut, expected) => {
    const { user, onChange } = renderEditor("");

    await user.click(content());
    await write(user, `${shortcut}Item`);

    await expectValue(onChange, expected);
  });

  it("starts a new paragraph on Enter and a new line on Shift+Enter", async () => {
    const { user, onChange } = renderEditor("");

    await user.click(content());
    await write(user, "one{Shift>}{Enter}{/Shift}two{Enter}three");

    await expectValue(onChange, "<p>one<br>two</p><p>three</p>");
  });

  it("keeps at most one blank line between paragraphs", async () => {
    const { user, onChange } = renderEditor("");

    await user.click(content());
    await write(user, "one{Enter}{Enter}{Enter}{Enter}{Enter}two");

    await expectValue(onChange, "<p>one</p><p></p><p>two</p>");
  });

  it("keeps at most one empty line inside a paragraph", async () => {
    const { user, onChange } = renderEditor("");

    await user.click(content());
    await write(
      user,
      "one{Shift>}{Enter}{Enter}{Enter}{Enter}{Enter}{/Shift}two",
    );

    await expectValue(onChange, "<p>one<br><br>two</p>");
  });

  it("leaves a list on Enter in an empty item", async () => {
    const { user, onChange } = renderEditor("");

    await user.click(content());
    await write(user, "- a{Enter}b{Enter}{Enter}after");

    await expectValue(
      onChange,
      "<ul><li><p>a</p></li><li><p>b</p></li></ul><p>after</p>",
    );
  });

  it("nests a list item one level and no deeper", async () => {
    const { user, onChange } = renderEditor("");

    await user.click(content());
    await write(user, "- a{Enter}b");
    expect(control("editor_indent")).toBeEnabled();
    await user.click(control("editor_indent"));
    await write(user, "{Enter}c");

    await expectValue(
      onChange,
      "<ul><li><p>a</p><ul><li><p>b</p></li><li><p>c</p></li></ul></li></ul>",
    );
    expect(control("editor_indent")).toBeDisabled();

    await user.keyboard("{Tab}");
    await user.click(control("editor_indent"));

    await expectValue(
      onChange,
      "<ul><li><p>a</p><ul><li><p>b</p></li><li><p>c</p></li></ul></li></ul>",
    );
  });

  it("outdents a nested list item", async () => {
    const { user, onChange } = renderEditor("");

    await user.click(content());
    await write(user, "- a{Enter}b");
    await user.click(control("editor_indent"));
    await expectValue(
      onChange,
      "<ul><li><p>a</p><ul><li><p>b</p></li></ul></li></ul>",
    );
    await user.click(control("editor_outdent"));

    await expectValue(onChange, "<ul><li><p>a</p></li><li><p>b</p></li></ul>");
  });

  it("disables the list level controls outside of lists", () => {
    renderEditor("<p>Hello</p>");

    expect(control("editor_indent")).toBeDisabled();
    expect(control("editor_outdent")).toBeDisabled();
  });

  it("undoes and redoes changes", async () => {
    const { user, onChange } = renderEditor("<p>Hello</p>");

    await user.click(content());
    await user.keyboard("{Control>}a{/Control}");
    await user.click(control("editor_bold"));
    await expectValue(onChange, "<p><strong>Hello</strong></p>");

    await user.click(control("editor_undo"));
    await expectValue(onChange, "<p>Hello</p>");

    await user.click(control("editor_redo"));
    await expectValue(onChange, "<p><strong>Hello</strong></p>");
  });

  it("keeps lists and the allowed formatting when pasting", async () => {
    const { user, onChange } = renderEditor("<p></p>");

    await user.click(content());
    paste({
      "text/html":
        '<h1 style="font-size:40px">Title</h1><p style="line-height:3;margin-bottom:40px"><span style="font-family:Comic Sans MS;color:red;font-size:30px"><strong>Bold</strong> <em>it</em></span> <a href="https://x.test">link</a><img src="x"></p><ol start="5" type="a"><li style="color:blue">one</li><li>two</li></ol>',
      "text/plain": "Title Bold it link one two",
    });

    await expectValue(
      onChange,
      "<p>Title</p><p><strong>Bold</strong> <em>it</em> link</p><ol><li><p>one</p></li><li><p>two</p></li></ol>",
    );
  });

  it("drops the empty paragraphs and spacing of pasted documents", async () => {
    const { user, onChange } = renderEditor("<p></p>");

    await user.click(content());
    paste({
      "text/html":
        '<meta charset="utf-8"><b style="font-weight:normal;" id="docs-internal-guid-1"><p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;"><span style="font-size:11pt;font-weight:700;">One</span></p><br><p dir="ltr"><span style="font-size:11pt;">Two</span></p><p><span>&nbsp;</span></p><p></p><p>Three</p></b>',
      "text/plain": "One\n\nTwo\n\nThree",
    });

    await expectValue(
      onChange,
      "<p><strong>One</strong></p><p>Two</p><p>Three</p>",
    );
  });

  it("nests the lists of Google Docs one level deep", async () => {
    const { user, onChange } = renderEditor("<p></p>");

    await user.click(content());
    paste({
      "text/html":
        '<b style="font-weight:normal;" id="docs-internal-guid-2"><ul><li dir="ltr" aria-level="1"><p dir="ltr" role="presentation"><span>a</span></p></li><ul><li aria-level="2"><p role="presentation"><span>b</span></p></li><ul><li aria-level="3"><p role="presentation"><span>c</span></p></li></ul></ul><li aria-level="1"><p role="presentation"><span>d</span></p></li></ul></b>',
      "text/plain": "a\nb\nc\nd",
    });

    await expectValue(
      onChange,
      "<ul><li><p>a</p><ul><li><p>b</p></li><li><p>c</p></li></ul></li><li><p>d</p></li></ul>",
    );
  });

  it("turns the list paragraphs of Word into lists", async () => {
    const { user, onChange } = renderEditor("<p></p>");

    await user.click(content());
    paste({
      "text/html": [
        "<html><body><!--StartFragment-->",
        "<p class=MsoNormal>Intro<o:p></o:p></p>",
        "<p class=MsoNormal><o:p>&nbsp;</o:p></p>",
        "<p class=MsoListParagraphCxSpFirst style='text-indent:-18.0pt;mso-list:l0 level1 lfo1'><![if !supportLists]><span style='font-family:Symbol;mso-list:Ignore'>·<span style='font:7.0pt \"Times New Roman\"'>&nbsp;&nbsp;&nbsp;</span></span><![endif]>First<o:p></o:p></p>",
        "<p class=MsoListParagraphCxSpMiddle style='mso-list:l0 level2 lfo1'><![if !supportLists]><span style='font-family:\"Courier New\";mso-list:Ignore'>o<span>&nbsp;&nbsp;</span></span><![endif]>Nested<o:p></o:p></p>",
        "<p class=MsoListParagraphCxSpLast style='mso-list:l0 level1 lfo1'><![if !supportLists]><span style='mso-list:Ignore'>·<span>&nbsp;</span></span><![endif]>Second<o:p></o:p></p>",
        "<p class=MsoListParagraph style='mso-list:l1 level1 lfo2'><![if !supportLists]><span style='mso-list:Ignore'>1.<span>&nbsp;</span></span><![endif]>Step<o:p></o:p></p>",
        "<!--EndFragment--></body></html>",
      ].join(""),
      "text/plain": "Intro\n\n·First\no Nested\n·Second\n1. Step",
    });

    await expectValue(
      onChange,
      "<p>Intro</p><ul><li><p>First</p><ul><li><p>Nested</p></li></ul></li><li><p>Second</p></li></ul><ol><li><p>Step</p></li></ol>",
    );
  });

  it("reads pasted plain text as paragraphs, lines and lists", async () => {
    const { user, onChange } = renderEditor("<p></p>");

    await user.click(content());
    paste({
      "text/plain":
        "About us\nZurich office\n\n\n\nWe offer:\n• Internships\n  - in Zurich\n• Theses\n\n1) Apply\n2) Meet us",
    });

    await expectValue(
      onChange,
      "<p>About us<br>Zurich office</p><p>We offer:</p><ul><li><p>Internships</p><ul><li><p>in Zurich</p></li></ul></li><li><p>Theses</p></li></ul><ol><li><p>Apply</p></li><li><p>Meet us</p></li></ol>",
    );
  });

  it("reports an emptied editor as an empty value", async () => {
    const { user, onChange } = renderEditor("<p>Hello</p>");

    await user.click(content());
    await user.keyboard("{Control>}a{/Control}{Backspace}");

    await expectValue(onChange, "");
  });
});
