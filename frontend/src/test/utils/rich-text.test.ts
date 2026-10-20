import { describe, expect, it } from "vitest";
import { richTextLength } from "../../utils/rich-text";

describe("the visible length of a description", () => {
  it("ignores the formatting markup", () => {
    expect(
      richTextLength("<p><strong>Bold</strong> text</p><p>line<br>break</p>"),
    ).toBe("Bold text\nline\nbreak".length);
  });

  it("counts entities as one character each", () => {
    expect(richTextLength("<p>&amp;&lt;</p>")).toBe(2);
  });

  it("counts an empty editor as empty", () => {
    expect(richTextLength("<p></p>")).toBe(0);
    expect(richTextLength("<p></p><p> <br> </p>")).toBe(0);
    expect(richTextLength("")).toBe(0);
  });

  it("matches the count of the backend for formatted runs", () => {
    const formatted = `<p>${"<strong>x</strong><em>y</em>".repeat(1250)}</p>`;

    expect(richTextLength(formatted)).toBe(2500);
  });

  it("counts every list item as its own line", () => {
    expect(
      richTextLength(
        "<p>Intro</p><ul><li><p>ab</p><ol><li><p>c</p></li></ol></li><li><p>d<br>e</p></li></ul>",
      ),
    ).toBe("Intro\nab\nc\nd\ne".length);
  });

  it("counts a list of the limit like the backend", () => {
    const items = "<li><p>xxxx</p></li>".repeat(500);

    expect(richTextLength(`<ul>${items}</ul>`)).toBe(2499);
    expect(richTextLength(`<ul>${items}<li><p>x</p></li></ul>`)).toBe(2501);
  });

  it("counts a blank line as one character", () => {
    expect(richTextLength("<p>a</p><p></p><p>b</p>")).toBe("a\n\nb".length);
  });

  it("counts only the spacing that reaches the booklet", () => {
    expect(
      richTextLength(
        "<p></p><p>a</p><p></p><p></p><p></p><p>b<br><br><br>c  d</p><p><br></p>",
      ),
    ).toBe("a\n\nb\n\nc  d".length);
    expect(richTextLength("<p><br>a<br> </p>")).toBe(1);
    expect(richTextLength("<p>a<br> <br>&nbsp;<br>b</p>")).toBe(4);
  });

  it("drops empty list items", () => {
    expect(
      richTextLength(
        "<ul><li><p>a</p></li><li><p></p></li><li><p>b</p></li></ul>",
      ),
    ).toBe(3);
  });

  it("counts characters the way the backend does", () => {
    expect(richTextLength("<p>Grüezi 🤖</p>")).toBe(8);
  });

  it("counts a description saved as plain text by its lines", () => {
    expect(richTextLength("First line\n\nSecond & <third>")).toBe(
      "First line\nSecond & <third>".length,
    );
  });
});
