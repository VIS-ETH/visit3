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

  it.each([
    ["<p>a</p></p><p>b</p>", 3],
    ["<p>a<p>b", 3],
    ["<ul><li>a<ul><li>b<ul><li>c</li></ul></li></ul></li></ul>", 5],
    ["<ul><li><p>a</p><p>b</p></li></ul>", 3],
    ["<table><tr><td>a</td><td>b</td></tr></table>", 2],
    ["<p>a</p><p></p><p></p><p>b</p>", 4],
    ["<p>a<br><br><br>b</p>", 4],
    ["<li>a</li><li>b</li>", 3],
    ["<p>x &amp; y &lt;z&gt;</p>", 9],
    ["<p>a</p>\n\n<p>b</p>", 3],
    ["<div><p>a</p></div><p>b</p>", 3],
    ["<p>a</p><ul><li></li></ul><p>b</p>", 3],
    ["<p>😀👍🏽</p>", 3],
    ["<p>a </p><p> </p><p>b</p>", 5],
    ["<pre>a\n\nb</pre>", 3],
    ["<h1>t</h1><p></p><h2>u</h2>", 4],
    ["<p><b>a</b><i>b</i></p>", 2],
    ["<ol><li>a</li></ol><p></p><ol><li>b</li></ol>", 4],
    ["<p>a</p><br><p>b</p>", 3],
    ["<blockquote><p>a</p><p></p><p>b</p></blockquote>", 4],
    ["<ul><li>a</li><p>b</p><li>c</li></ul>", 5],
    ["<p>a<script>xx</script>b</p>", 2],
    ["<p>a</p><style>p{}</style>", 1],
    ["<p><p></p></p><p>a</p>", 1],
    ["  <p>a</p>", 1],
    ["a\r\nb\n\nc", 5],
    ["<p>a</p><ul><li>b</li></ul><p></p><p>c</p>", 6],
    ["<ul><li><ul><li>x</li></ul></li></ul>", 1],
    ["<p>a</p><p>​</p><p>b</p>", 5],
    ["<p>a</p><p>　</p><p>b</p>", 4],
    ["<p>a<div>b</div>c</p>", 5],
    ["<p>a</p><!-- c --><p>b</p>", 3],
    ["<p>a<br></p><p>b</p>", 3],
    ["<p><br></p><p>b</p>", 1],
    ["<ol><li>a<br><br>b</li></ol>", 4],
  ])("counts %j like the backend", (input, length) => {
    expect(richTextLength(input)).toBe(length);
  });
});
