from dataclasses import dataclass, replace
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
BLOCK_TAGS = {
    "p",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "blockquote",
    "pre",
    "ul",
    "ol",
    "table",
    "tr",
}
HIDDEN_TAGS = {"script", "style", "template", "noscript", "iframe", "object", "head"}


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


LINE_BREAK = LineBreak()
Inline = Run | LineBreak
Paragraph = list[Inline]


class _RichTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[Paragraph] = []
        self.current: Paragraph = []
        self.open_marks: list[str] = []
        self.hidden_depth = 0

    def _marks(self) -> Marks:
        active = set(self.open_marks)
        return Marks(
            bold="bold" in active,
            italic="italic" in active,
            underline="underline" in active,
            strike="strike" in active,
        )

    def _close_paragraph(self) -> None:
        if self.current:
            self.paragraphs.append(self.current)
        self.current = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in HIDDEN_TAGS:
            self.hidden_depth += 1
        elif tag in MARK_TAGS:
            self.open_marks.append(MARK_TAGS[tag])
        elif tag == "br":
            self.current.append(LINE_BREAK)
        elif tag in BLOCK_TAGS:
            self._close_paragraph()

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
        elif tag in BLOCK_TAGS:
            self._close_paragraph()

    def handle_data(self, data: str) -> None:
        if self.hidden_depth or not data:
            return
        self.current.append(Run(data, self._marks()))

    def result(self) -> list[Paragraph]:
        self.close()
        self._close_paragraph()
        return self.paragraphs


def _is_markup(value: str) -> bool:
    return value.lstrip().startswith("<")


def _plain_paragraphs(value: str) -> list[Paragraph]:
    return [
        [Run(line, Marks())]
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


def _paragraph_text(paragraph: Paragraph) -> str:
    return "".join(item.text if isinstance(item, Run) else "\n" for item in paragraph)


def parse_rich_text(value: str) -> list[Paragraph]:
    if not _is_markup(value):
        paragraphs = _plain_paragraphs(value)
    else:
        parser = _RichTextParser()
        parser.feed(value)
        paragraphs = parser.result()
    return [
        _merge(paragraph)
        for paragraph in paragraphs
        if _paragraph_text(paragraph).strip()
    ]


def _run_html(run: Run) -> str:
    html = escape(run.text, quote=True).replace("&#x27;", "'")
    for mark, tag in reversed(MARK_ORDER):
        if getattr(run.marks, mark):
            html = f"<{tag}>{html}</{tag}>"
    return html


def sanitize_rich_text(value: str) -> str:
    return "".join(
        "<p>"
        + "".join(
            _run_html(item) if isinstance(item, Run) else "<br>" for item in paragraph
        )
        + "</p>"
        for paragraph in parse_rich_text(value)
    )


def rich_text_plain(value: str) -> str:
    return "\n".join(_paragraph_text(paragraph) for paragraph in parse_rich_text(value))


def rich_text_length(value: str) -> int:
    return len(rich_text_plain(value))


def rich_text_blocks(value: str) -> list[list[dict[str, object]]]:
    return [
        [
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
        for paragraph in parse_rich_text(value)
    ]
