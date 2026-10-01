import re
from dataclasses import dataclass, field, replace
from html import escape
from html.parser import HTMLParser

MARK_TAGS = {
    "strong": "bold",
    "b": "bold",
    "em": "italic",
    "i": "italic",
    "u": "underline",
    "s": "strike",
    "strike": "strike",
    "del": "strike",
}
MARK_ORDER = (
    ("bold", "strong"),
    ("italic", "em"),
    ("underline", "u"),
    ("strike", "s"),
)
LIST_TAGS = {"ul": False, "ol": True}
BLOCK_TAGS = {
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
}
HIDDEN_TAGS = {"script", "style", "template", "noscript", "iframe", "object", "head"}
MAX_LIST_LEVEL = 2
SOURCE_NEWLINE = re.compile(r"[ \t]*[\r\n]+[ \t]*")
BULLETS = ("•", "–")
NESTED_INDENT = "   "


@dataclass(frozen=True)
class Marks:
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False


@dataclass(frozen=True)
class Run:
    text: str
    marks: Marks


class LineBreak:
    pass


class Blank:
    pass


LINE_BREAK = LineBreak()
BLANK = Blank()
Inline = Run | LineBreak
Paragraph = list[Inline]


@dataclass
class Entry:
    inlines: Paragraph
    level: int = 0
    ordered: bool = False
    blank: bool = False
    joined: bool = False


@dataclass
class ListItem:
    inlines: Paragraph
    lists: list["ListBlock"] = field(default_factory=lambda: [])


@dataclass
class ListBlock:
    ordered: bool
    items: list[ListItem] = field(default_factory=lambda: [])


Block = Paragraph | ListBlock | Blank


@dataclass
class _OpenItem:
    level: int
    entry: Entry | None = None


def _text(paragraph: Paragraph) -> str:
    return "".join(item.text if isinstance(item, Run) else "\n" for item in paragraph)


def _visible(paragraph: Paragraph) -> bool:
    return bool(_text(paragraph).strip())


class _RichTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[Entry] = []
        self.current: Paragraph = []
        self.open_marks: list[str] = []
        self.hidden_depth = 0
        self.lists: list[bool] = []
        self.items: list[_OpenItem] = []
        self.paragraph_starts: list[int] = []

    def _marks(self) -> Marks:
        active = set(self.open_marks)
        return Marks(
            bold="bold" in active,
            italic="italic" in active,
            underline="underline" in active,
            strike="strike" in active,
        )

    def _open_item(self) -> _OpenItem | None:
        if self.items and self.items[-1].level == len(self.lists):
            return self.items[-1]
        return None

    def _flush(self) -> None:
        inlines, self.current = self.current, []
        if not _visible(inlines):
            return
        item = self._open_item()
        level = min(len(self.lists), MAX_LIST_LEVEL)
        entry = Entry(
            inlines,
            level,
            self.lists[level - 1] if level else False,
            joined=item is not None
            and item.entry is not None
            and item.entry is self.entries[-1],
        )
        self.entries.append(entry)
        if item is not None:
            item.entry = entry

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in HIDDEN_TAGS:
            self.hidden_depth += 1
        elif tag in MARK_TAGS:
            self.open_marks.append(MARK_TAGS[tag])
        elif tag == "br":
            self.current.append(LINE_BREAK)
        elif tag in LIST_TAGS:
            self._flush()
            self.lists.append(LIST_TAGS[tag])
        elif tag == "li":
            self._flush()
            self.items.append(_OpenItem(len(self.lists)))
        elif tag in BLOCK_TAGS:
            self._flush()
            if tag == "p":
                self.paragraph_starts.append(len(self.entries))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self.current.append(LINE_BREAK)

    def handle_endtag(self, tag: str) -> None:
        if tag in HIDDEN_TAGS:
            self.hidden_depth = max(self.hidden_depth - 1, 0)
        elif tag in MARK_TAGS:
            mark = MARK_TAGS[tag]
            if mark in self.open_marks:
                index = len(self.open_marks) - 1 - self.open_marks[::-1].index(mark)
                del self.open_marks[index]
        elif tag in LIST_TAGS:
            self._flush()
            if self.lists:
                self.lists.pop()
        elif tag == "li":
            self._flush()
            if self.items:
                self.items.pop()
        elif tag in BLOCK_TAGS:
            self._flush()
            if tag == "p" and self.paragraph_starts:
                start = self.paragraph_starts.pop()
                if not self.lists and start == len(self.entries):
                    self.entries.append(Entry([], blank=True))

    def handle_data(self, data: str) -> None:
        if self.hidden_depth or not data:
            return
        self.current.append(Run(data, self._marks()))

    def result(self) -> list[Entry]:
        self.close()
        self._flush()
        return self.entries


def _is_markup(value: str) -> bool:
    return value.lstrip().startswith("<")


def _plain_entries(value: str) -> list[Entry]:
    return [
        Entry([Run(line, Marks())])
        for line in value.replace("\r\n", "\n").split("\n")
        if line.strip()
    ]


def _merge(paragraph: Paragraph) -> Paragraph:
    merged: Paragraph = []
    for item in paragraph:
        previous = merged[-1] if merged else None
        if (
            isinstance(item, Run)
            and isinstance(previous, Run)
            and previous.marks == item.marks
        ):
            merged[-1] = replace(previous, text=previous.text + item.text)
        else:
            merged.append(item)
    return merged


def _lines_of(paragraph: Paragraph) -> list[Paragraph]:
    lines: list[Paragraph] = [[]]
    for item in paragraph:
        if isinstance(item, LineBreak):
            lines.append([])
        else:
            lines[-1].append(replace(item, text=SOURCE_NEWLINE.sub(" ", item.text)))
    return lines


def _limit_breaks(paragraph: Paragraph) -> Paragraph:
    kept: list[Paragraph] = []
    for line in _lines_of(paragraph):
        if _visible(line):
            kept.append(line)
        elif kept and kept[-1]:
            kept.append([])
    if kept and not kept[-1]:
        kept.pop()
    result: Paragraph = []
    for index, line in enumerate(kept):
        if index:
            result.append(LINE_BREAK)
        result.extend(line)
    return result


def _tidy(entry: Entry) -> Entry:
    return replace(entry, inlines=_limit_breaks(entry.inlines))


def _arrange(entries: list[Entry]) -> list[Entry]:
    arranged: list[Entry] = []
    for entry in entries:
        if entry.blank:
            if arranged and not arranged[-1].blank:
                arranged.append(entry)
        elif entry.joined and arranged and not arranged[-1].blank:
            previous = arranged[-1]
            arranged[-1] = replace(
                previous,
                inlines=_merge([*previous.inlines, LINE_BREAK, *entry.inlines]),
            )
        elif _visible(entry.inlines):
            arranged.append(replace(entry, inlines=_merge(entry.inlines)))
    while arranged and arranged[-1].blank:
        arranged.pop()
    return arranged


def _group(entries: list[Entry]) -> list[Block]:
    blocks: list[Block] = []
    for entry in entries:
        if entry.blank:
            blocks.append(BLANK)
            continue
        if not entry.level:
            blocks.append(entry.inlines)
            continue
        top = blocks[-1] if blocks and isinstance(blocks[-1], ListBlock) else None
        if entry.level > 1 and top is not None:
            parent = top.items[-1]
            if not parent.lists or parent.lists[-1].ordered != entry.ordered:
                parent.lists.append(ListBlock(entry.ordered))
            parent.lists[-1].items.append(ListItem(entry.inlines))
            continue
        if top is None or top.ordered != entry.ordered:
            top = ListBlock(entry.ordered)
            blocks.append(top)
        top.items.append(ListItem(entry.inlines))
    return blocks


def _entries(value: str) -> list[Entry]:
    if not _is_markup(value):
        return _plain_entries(value)
    parser = _RichTextParser()
    parser.feed(value)
    return parser.result()


def parse_rich_text(value: str, tidy: bool = False) -> list[Block]:
    entries = _entries(value)
    if tidy:
        entries = [_tidy(entry) for entry in entries]
    return _group(_arrange(entries))


def _run_html(run: Run) -> str:
    html = escape(run.text, quote=True).replace("&#x27;", "'")
    for mark, tag in reversed(MARK_ORDER):
        if getattr(run.marks, mark):
            html = f"<{tag}>{html}</{tag}>"
    return html


def _paragraph_html(paragraph: Paragraph) -> str:
    return "".join(
        _run_html(item) if isinstance(item, Run) else "<br>" for item in paragraph
    )


def _list_html(block: ListBlock) -> str:
    tag = "ol" if block.ordered else "ul"
    items = "".join(
        "<li><p>"
        + _paragraph_html(item.inlines)
        + "</p>"
        + "".join(_list_html(child) for child in item.lists)
        + "</li>"
        for item in block.items
    )
    return f"<{tag}>{items}</{tag}>"


def _block_html(block: Block) -> str:
    if isinstance(block, Blank):
        return "<p></p>"
    if isinstance(block, ListBlock):
        return _list_html(block)
    return f"<p>{_paragraph_html(block)}</p>"


def sanitize_rich_text(value: str) -> str:
    return "".join(_block_html(block) for block in parse_rich_text(value, tidy=True))


def _alphabetic(number: int) -> str:
    letters = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(ord("a") + remainder) + letters
    return letters


def _marker(ordered: bool, depth: int, index: int) -> str:
    if not ordered:
        return f"{BULLETS[depth]} "
    return f"{_alphabetic(index + 1) if depth else index + 1}. "


def _list_lines(block: ListBlock, depth: int, marked: bool) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(block.items):
        text = _text(item.inlines)
        if marked:
            prefix = NESTED_INDENT * depth
            marker = _marker(block.ordered, depth, index)
            hanging = "\n" + prefix + " " * len(marker)
            text = prefix + marker + text.replace("\n", hanging)
        lines.append(text)
        for child in item.lists:
            lines.extend(_list_lines(child, depth + 1, marked))
    return lines


def _lines(value: str, marked: bool) -> list[str]:
    lines: list[str] = []
    for block in parse_rich_text(value):
        if isinstance(block, Blank):
            lines.append("")
        elif isinstance(block, ListBlock):
            lines.extend(_list_lines(block, 0, marked))
        else:
            lines.append(_text(block))
    return lines


def rich_text_plain(value: str) -> str:
    return "\n".join(_lines(value, marked=True))


def rich_text_length(value: str) -> int:
    return len("\n".join(_lines(value, marked=False)))


def _inline_data(paragraph: Paragraph) -> list[dict[str, object]]:
    return [
        {
            "text": item.text,
            "bold": item.marks.bold,
            "italic": item.marks.italic,
            "underline": item.marks.underline,
            "strike": item.marks.strike,
        }
        if isinstance(item, Run)
        else {"break": True}
        for item in paragraph
    ]


def _list_data(block: ListBlock) -> dict[str, object]:
    return {
        "ordered": block.ordered,
        "items": [
            {
                "inlines": _inline_data(item.inlines),
                "lists": [_list_data(child) for child in item.lists],
            }
            for item in block.items
        ],
    }


def rich_text_blocks(value: str) -> list[object]:
    blocks: list[object] = []
    for block in parse_rich_text(value):
        if isinstance(block, Blank):
            blocks.append({"blank": True})
        elif isinstance(block, ListBlock):
            blocks.append(_list_data(block))
        else:
            blocks.append(_inline_data(block))
    return blocks
