from html.parser import HTMLParser

BLOCK_TAGS = frozenset(
    {
        "blockquote",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "li",
        "ol",
        "p",
        "table",
        "tr",
        "ul",
    }
)
SKIPPED_TAGS = frozenset({"head", "script", "style", "title"})


class _PlainTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._link_urls: list[str] = []
        self._link_texts: list[str] = []
        self._skipped = 0

    def _append(self, text: str) -> None:
        if self._link_texts:
            self._link_texts[-1] += text
        else:
            self._chunks.append(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in SKIPPED_TAGS:
            self._skipped += 1
        elif tag == "a":
            self._link_urls.append(dict(attrs).get("href") or "")
            self._link_texts.append("")
        elif tag in BLOCK_TAGS:
            self._append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in BLOCK_TAGS:
            self._append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIPPED_TAGS:
            self._skipped = max(self._skipped - 1, 0)
        elif tag == "a" and self._link_urls:
            url = self._link_urls.pop()
            label = self._link_texts.pop().strip()
            self._append(f"{label} ({url})" if url else label)
        elif tag in BLOCK_TAGS:
            self._append("\n")

    def handle_data(self, data: str) -> None:
        if self._skipped == 0:
            self._append(data)

    def collected(self) -> str:
        return "".join(self._chunks) + "".join(self._link_texts)


def _collapse(raw: str) -> str:
    lines: list[str] = []
    for line in raw.splitlines():
        collapsed = " ".join(line.split())
        if collapsed or (lines and lines[-1]):
            lines.append(collapsed)
    return "\n".join(lines).strip()


def html_to_plain_text(html: str) -> str:
    extractor = _PlainTextExtractor()
    extractor.feed(html)
    extractor.close()
    return _collapse(extractor.collected())
