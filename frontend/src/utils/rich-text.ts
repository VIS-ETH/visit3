type Inline = string | null;

interface Entry {
  inlines: Inline[];
  blank: boolean;
}

const LINE_BREAK = null;
const MARKUP = /^\s*</;
const SOURCE_NEWLINE = /[ \t]*[\r\n]+[ \t]*/g;
const BYTE_ORDER_MARK = String.fromCharCode(0xfeff);
const PYTHON_SPACES = new Set(
  [0x1c, 0x1d, 0x1e, 0x1f, 0x85].map((code) => String.fromCharCode(code)),
);
const HIDDEN_TAGS = new Set([
  "script",
  "style",
  "template",
  "noscript",
  "iframe",
  "object",
  "head",
]);
const LIST_TAGS = new Set(["ul", "ol"]);
const BLOCK_TAGS = new Set([
  "p",
  "div",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "blockquote",
  "pre",
  "table",
  "tr",
]);

const textOf = (inlines: Inline[]) =>
  inlines.map((inline) => inline ?? "\n").join("");

const isSpace = (character: string) =>
  (character !== BYTE_ORDER_MARK && /\s/.test(character)) ||
  PYTHON_SPACES.has(character);

const isBlank = (text: string) => Array.from(text).every(isSpace);

const visible = (inlines: Inline[]) => !isBlank(textOf(inlines));

class EntryCollector {
  entries: Entry[] = [];
  current: Inline[] = [];
  lists = 0;
  paragraphStarts: number[] = [];

  flush() {
    const inlines = this.current;
    this.current = [];
    if (visible(inlines)) this.entries.push({ inlines, blank: false });
  }

  start(tag: string) {
    if (tag === "br") {
      this.current.push(LINE_BREAK);
    } else if (LIST_TAGS.has(tag)) {
      this.flush();
      this.lists += 1;
    } else if (tag === "li") {
      this.flush();
    } else if (BLOCK_TAGS.has(tag)) {
      this.flush();
      if (tag === "p") this.paragraphStarts.push(this.entries.length);
    }
  }

  end(tag: string) {
    if (LIST_TAGS.has(tag)) {
      this.flush();
      this.lists = Math.max(this.lists - 1, 0);
    } else if (tag === "li") {
      this.flush();
    } else if (BLOCK_TAGS.has(tag)) {
      this.flush();
      const start = tag === "p" ? this.paragraphStarts.pop() : undefined;
      if (start === this.entries.length && this.lists === 0) {
        this.entries.push({ inlines: [], blank: true });
      }
    }
  }
}

const walk = (node: Node, collector: EntryCollector, hidden: boolean) => {
  if (node.nodeType === Node.TEXT_NODE) {
    if (!hidden && node.textContent) collector.current.push(node.textContent);
    return;
  }
  if (node.nodeType !== Node.ELEMENT_NODE) return;
  const tag = (node as Element).localName;
  collector.start(tag);
  node.childNodes.forEach((child) =>
    walk(child, collector, hidden || HIDDEN_TAGS.has(tag)),
  );
  if (tag !== "br") collector.end(tag);
};

const markupEntries = (html: string) => {
  const collector = new EntryCollector();
  walk(
    new DOMParser().parseFromString(html, "text/html").body,
    collector,
    false,
  );
  collector.flush();
  return collector.entries;
};

const plainEntries = (text: string): Entry[] =>
  text
    .replaceAll("\r\n", "\n")
    .split("\n")
    .filter((line) => !isBlank(line))
    .map((line) => ({ inlines: [line], blank: false }));

const lines = (inlines: Inline[]) =>
  inlines.reduce<Inline[][]>(
    (result, inline) => {
      if (inline === LINE_BREAK) result.push([]);
      else result[result.length - 1].push(inline.replace(SOURCE_NEWLINE, " "));
      return result;
    },
    [[]],
  );

const limitBreaks = (inlines: Inline[]) => {
  const kept: Inline[][] = [];
  for (const line of lines(inlines)) {
    if (visible(line)) kept.push(line);
    else if (kept.length > 0 && kept[kept.length - 1].length > 0) kept.push([]);
  }
  if (kept.length > 0 && kept[kept.length - 1].length === 0) kept.pop();
  return kept.flatMap((line, index) => (index ? [LINE_BREAK, ...line] : line));
};

const arrange = (entries: Entry[]) => {
  const arranged: Entry[] = [];
  for (const entry of entries) {
    if (entry.blank) {
      if (arranged.length > 0 && !arranged[arranged.length - 1].blank) {
        arranged.push(entry);
      }
    } else if (visible(entry.inlines)) {
      arranged.push(entry);
    }
  }
  while (arranged.length > 0 && arranged[arranged.length - 1].blank) {
    arranged.pop();
  }
  return arranged;
};

export const richTextLength = (value: string) => {
  const entries = (
    MARKUP.test(value) ? markupEntries(value) : plainEntries(value)
  ).map((entry) => ({ ...entry, inlines: limitBreaks(entry.inlines) }));
  const text = arrange(entries)
    .map((entry) => textOf(entry.inlines))
    .join("\n");
  return Array.from(text).length;
};
