import { describe, expect, it } from "vitest";
import { richTextLength, richTextPlain } from "../../utils/rich-text";

describe("the visible text of a description", () => {
  it("ignores the formatting markup", () => {
    expect(
      richTextPlain("<p><strong>Bold</strong> text</p><p>line<br>break</p>"),
    ).toBe("Bold text\nline\nbreak");
  });

  it("counts entities as one character each", () => {
    expect(richTextLength("<p>&amp;&lt;</p>")).toBe(2);
  });

  it("counts an empty editor as empty", () => {
    expect(richTextLength("<p></p>")).toBe(0);
    expect(richTextLength("")).toBe(0);
  });

  it("matches the count of the backend for formatted runs", () => {
    const formatted = `<p>${"<strong>x</strong><em>y</em>".repeat(1250)}</p>`;

    expect(richTextLength(formatted)).toBe(2500);
  });
});
