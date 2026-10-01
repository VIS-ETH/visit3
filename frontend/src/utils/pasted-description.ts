const WORD_LIST_LEVEL = /mso-list:\s*\S+\s+level(\d+)/i;
const WORD_LIST_MARKER = /mso-list:\s*ignore/i;
const ORDERED_MARKER = /^\(?(\d+|[a-z]|[ivxlcdm]+)[.)]$/i;
const BULLET_LINE = /^(\s*)[-*•◦▪‣·–]\s+(.*)$/u;
const NUMBER_LINE = /^(\s*)\d{1,3}[.)]\s+(.*)$/;
const NESTED_INDENT = /^(?: {2,}|\t)/;
const BLANK_TEXT = /^\s*$/;
const STRAY_LISTS = "ul > ul, ul > ol, ol > ul, ol > ol";
const BLOCKS = new Set([
  "P",
  "DIV",
  "UL",
  "OL",
  "LI",
  "H1",
  "H2",
  "H3",
  "H4",
  "H5",
  "H6",
  "TABLE",
  "BLOCKQUOTE",
  "PRE",
]);

type ListTag = "UL" | "OL";

class ListBuilder {
  lists: HTMLElement[] = [];
  readonly doc: Document;

  constructor(doc: Document) {
    this.doc = doc;
  }

  add(level: number, tag: ListTag, place: (list: HTMLElement) => void) {
    const depth = Math.min(Math.max(level, 1), this.lists.length + 1, 2);
    this.lists = this.lists.slice(0, depth);
    if (this.lists[depth - 1]?.tagName !== tag) {
      const list = this.doc.createElement(tag);
      if (depth === 1) place(list);
      else this.lists[0].lastElementChild?.append(list);
      this.lists[depth - 1] = list;
      this.lists = this.lists.slice(0, depth);
    }
    const item = this.doc.createElement("li");
    const body = this.doc.createElement("p");
    item.append(body);
    this.lists[depth - 1].append(item);
    return body;
  }
}

const wordListLevel = (element: Element) => {
  const match = WORD_LIST_LEVEL.exec(element.getAttribute("style") ?? "");
  return match ? Number(match[1]) : null;
};

const convertWordLists = (doc: Document) => {
  let builder = new ListBuilder(doc);
  for (const paragraph of Array.from(doc.querySelectorAll("p"))) {
    const level = wordListLevel(paragraph);
    if (level === null) continue;
    const marker = Array.from(paragraph.querySelectorAll("span")).find((span) =>
      WORD_LIST_MARKER.test(span.getAttribute("style") ?? ""),
    );
    const markerText = (marker?.textContent ?? "").replace(/\s/g, "");
    marker?.remove();
    if (paragraph.previousElementSibling !== builder.lists[0]) {
      builder = new ListBuilder(doc);
    }
    const body = builder.add(
      level,
      ORDERED_MARKER.test(markerText) ? "OL" : "UL",
      (list) => paragraph.before(list),
    );
    body.append(...Array.from(paragraph.childNodes));
    paragraph.remove();
  }
};

const nestStrayLists = (doc: Document) => {
  for (const list of Array.from(doc.querySelectorAll(STRAY_LISTS))) {
    const previous = list.previousElementSibling;
    if (previous?.tagName === "LI") {
      previous.append(list);
    } else {
      const item = doc.createElement("li");
      list.before(item);
      item.append(list);
    }
  }
};

const dropPastedSpacing = (doc: Document) => {
  for (const paragraph of Array.from(doc.querySelectorAll("p"))) {
    if (BLANK_TEXT.test(paragraph.textContent)) paragraph.remove();
  }
  for (const lineBreak of Array.from(doc.querySelectorAll("br"))) {
    const neighbours = [
      lineBreak.previousElementSibling,
      lineBreak.nextElementSibling,
    ];
    if (neighbours.some((element) => element && BLOCKS.has(element.tagName))) {
      lineBreak.remove();
    }
  }
};

export const cleanPastedHtml = (html: string) => {
  const doc = new DOMParser().parseFromString(html, "text/html");
  convertWordLists(doc);
  nestStrayLists(doc);
  dropPastedSpacing(doc);
  return doc.body.innerHTML;
};

export const plainTextToDom = (text: string) => {
  const doc = document.implementation.createHTMLDocument();
  const root = doc.createElement("div");
  let builder = new ListBuilder(doc);
  let current: HTMLElement | null = null;
  for (const line of text.replace(/\r\n?/g, "\n").split("\n")) {
    if (BLANK_TEXT.test(line)) {
      current = null;
      builder = new ListBuilder(doc);
      continue;
    }
    const bullet = BULLET_LINE.exec(line);
    const number = bullet ? null : NUMBER_LINE.exec(line);
    const item = bullet ?? number;
    if (item) {
      const level = NESTED_INDENT.test(item[1]) ? 2 : 1;
      current = builder.add(level, bullet ? "UL" : "OL", (list) =>
        root.append(list),
      );
      current.append(item[2].trim());
    } else if (current) {
      current.append(doc.createElement("br"), line.trim());
    } else {
      current = doc.createElement("p");
      current.append(line.trim());
      root.append(current);
      builder = new ListBuilder(doc);
    }
  }
  return root;
};
