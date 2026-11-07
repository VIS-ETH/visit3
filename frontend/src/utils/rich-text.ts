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
const RAW_TEXT_TAGS = new Set(["script", "style"]);
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

const tagPattern = () =>
  /<!--[\s\S]*?-->|<[!?][^>]*>|<(\/?)([a-zA-Z][^\t\n\r\f />\0]*)(?:[^>"']|"[^"]*"|'[^']*')*>/g;

let entityDecoder: HTMLTextAreaElement | null = null;

const decodeEntities = (text: string) => {
  if (!text.includes("&")) return text;
  entityDecoder ??= new DOMParser()
    .parseFromString("", "text/html")
    .createElement("textarea");
  entityDecoder.innerHTML = text;
  return entityDecoder.value;
};

const rawTextEnd = (html: string, from: number, tag: string) => {
  const end = html.slice(from).search(new RegExp(`</${tag}[\\s/>]`, "i"));
  return end < 0 ? html.length : from + end;
};

const markupEntries = (html: string) => {
  const collector = new EntryCollector();
  const pattern = tagPattern();
  let hidden = 0;
  let last = 0;
  const addText = (text: string) => {
    if (hidden === 0 && text) collector.current.push(decodeEntities(text));
  };
  for (let match = pattern.exec(html); match; match = pattern.exec(html)) {
    addText(html.slice(last, match.index));
    last = pattern.lastIndex;
    const [token, closing, name] = match;
    if (!name) continue;
    const tag = name.toLowerCase();
    if (closing) {
      if (HIDDEN_TAGS.has(tag)) hidden = Math.max(hidden - 1, 0);
      else collector.end(tag);
    } else if (token.endsWith("/>")) {
      if (tag === "br") collector.start(tag);
    } else if (HIDDEN_TAGS.has(tag)) {
      hidden += 1;
      if (RAW_TEXT_TAGS.has(tag)) {
        last = rawTextEnd(html, last, tag);
        pattern.lastIndex = last;
      }
    } else {
      collector.start(tag);
    }
  }
  addText(html.slice(last));
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
