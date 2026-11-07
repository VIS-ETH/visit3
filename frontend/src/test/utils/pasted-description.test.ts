import { describe, expect, it } from "vitest";
import { plainTextToDom } from "../../utils/pasted-description";

const html = (text: string) => plainTextToDom(text).innerHTML;

describe("pasted plain text", () => {
  it("keeps a closing sentence after a list as its own paragraph", () => {
    expect(
      html(
        "We offer:\n- Internships\n- Theses\nWe look forward to meeting you.",
      ),
    ).toBe(
      "<p>We offer:</p><ul><li><p>Internships</p></li><li><p>Theses</p></li></ul><p>We look forward to meeting you.</p>",
    );
  });

  it("keeps an indented line in its list item", () => {
    expect(html("- Internships\n  in Zurich")).toBe(
      "<ul><li><p>Internships<br>in Zurich</p></li></ul>",
    );
  });

  it("keeps underscores inside a URL", () => {
    expect(html("Jobs: https://acme.test/_careers_")).toBe(
      "<p>Jobs: https://acme.test/_careers_</p>",
    );
  });

  it("does not turn a sentence starting with an ordinal into a list", () => {
    expect(html("1. FC Zürich ist unser Partner.")).toBe(
      "<p>1. FC Zürich ist unser Partner.</p>",
    );
  });
});
