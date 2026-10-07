import pytest

from app.core.rich_text import (
    rich_text_blocks,
    rich_text_length,
    rich_text_plain,
    sanitize_rich_text,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("<p>Hello</p>", "<p>Hello</p>"),
        (
            "<p><strong>Bold</strong> <em>italic</em> <u>under</u> <s>gone</s></p>",
            "<p><strong>Bold</strong> <em>italic</em> <u>under</u> <s>gone</s></p>",
        ),
        (
            "<p><b>b</b><i>i</i><strike>s</strike><del>d</del></p>",
            "<p><strong>b</strong><em>i</em><s>sd</s></p>",
        ),
        ("<p>one<br>two</p><p>three</p>", "<p>one<br>two</p><p>three</p>"),
        (
            "<p><strong><em>both</em></strong></p>",
            "<p><strong><em>both</em></strong></p>",
        ),
        ("<p><strong>a</strong><strong>b</strong></p>", "<p><strong>ab</strong></p>"),
    ],
)
def test_the_allowed_formatting_is_kept(raw: str, expected: str):
    assert sanitize_rich_text(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("<h1>Title</h1><p>Body</p>", "<p>Title</p><p>Body</p>"),
        (
            '<p><a href="javascript:alert(1)">link</a></p>',
            "<p>link</p>",
        ),
        ('<p><img src="x" onerror="alert(1)">x</p>', "<p>x</p>"),
        ("<p>a<script>alert(1)</script>b</p>", "<p>ab</p>"),
        ("<style>p{color:red}</style><p>styled</p>", "<p>styled</p>"),
        (
            '<p><span style="color:red">red</span></p>',
            "<p>red</p>",
        ),
        (
            '<p><strong onclick="x()" class="y">bold</strong></p>',
            "<p><strong>bold</strong></p>",
        ),
        (
            '<ul class="x"><li style="color:red">one</li></ul>',
            "<ul><li><p>one</p></li></ul>",
        ),
        (
            '<ol start="3" type="a"><li>one</li></ol>',
            "<ol><li><p>one</p></li></ol>",
        ),
        (
            "<ul><li><p>a<script>alert(1)</script></p></li></ul>",
            "<ul><li><p>a</p></li></ul>",
        ),
        ("<p>&lt;script&gt; &amp; &quot;</p>", "<p>&lt;script&gt; &amp; &quot;</p>"),
        ("<!-- note --><p>c</p>", "<p>c</p>"),
    ],
)
def test_everything_outside_the_allow_list_is_removed(raw: str, expected: str):
    assert sanitize_rich_text(raw) == expected


def test_an_unfinished_tag_never_becomes_markup():
    assert "<b" not in sanitize_rich_text("<p>a <b")


def test_empty_content_becomes_empty():
    assert sanitize_rich_text("<p></p><p> <br> </p>") == ""


def test_plain_text_keeps_its_lines_as_paragraphs():
    assert sanitize_rich_text("First line\nSecond & <third>") == (
        "<p>First line</p><p>Second &amp; &lt;third&gt;</p>"
    )


def test_the_visible_text_ignores_the_markup():
    html = "<p><strong>Bold</strong> text</p><p>line<br>break</p>"

    assert rich_text_plain(html) == "Bold text\nline\nbreak"
    assert rich_text_length(html) == len("Bold text\nline\nbreak")


def test_entities_count_as_one_character():
    assert rich_text_length("<p>&amp;&lt;</p>") == 2


def test_blocks_describe_paragraphs_and_formatted_runs():
    html = "<p>Plain <strong><u>bold under</u></strong><br><s>gone</s></p><p>#x</p>"

    assert rich_text_blocks(html) == [
        [
            {
                "text": "Plain ",
                "bold": False,
                "italic": False,
                "underline": False,
                "strike": False,
            },
            {
                "text": "bold under",
                "bold": True,
                "italic": False,
                "underline": True,
                "strike": False,
            },
            {"break": True},
            {
                "text": "gone",
                "bold": False,
                "italic": False,
                "underline": False,
                "strike": True,
            },
        ],
        [
            {
                "text": "#x",
                "bold": False,
                "italic": False,
                "underline": False,
                "strike": False,
            },
        ],
    ]


@pytest.mark.parametrize(
    "html",
    [
        "<ul><li><p>one</p></li><li><p>two</p></li></ul>",
        "<ol><li><p>first</p></li><li><p>second</p></li></ol>",
        "<ul><li><p>a</p><ol><li><p>b</p></li><li><p>c</p></li></ol></li></ul>",
        "<ol><li><p><strong>Bold</strong> and <em>more</em><br>next</p></li></ol>",
        "<p>Intro</p><ul><li><p>a</p></li></ul><p>Outro</p>",
        "<ul><li><p>a</p></li></ul><ol><li><p>b</p></li></ol>",
        "<p>a</p><p></p><p>b</p>",
        "<p>one<br><br>two</p>",
    ],
)
def test_lists_and_spacing_survive_unchanged(html: str):
    assert sanitize_rich_text(html) == html


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "<ul><li>one</li><li>two</li></ul>",
            "<ul><li><p>one</p></li><li><p>two</p></li></ul>",
        ),
        (
            "<ul><li><p>a</p><p>b</p></li></ul>",
            "<ul><li><p>a<br>b</p></li></ul>",
        ),
        (
            "<ul><li><p>a<br><br></p><p><br>b</p></li></ul>",
            "<ul><li><p>a<br>b</p></li></ul>",
        ),
        (
            "<ul><li>a</li></ul><ul><li>b</li></ul>",
            "<ul><li><p>a</p></li><li><p>b</p></li></ul>",
        ),
        (
            "<ul><li>a</li><li></li><li> <br> </li><li>b</li></ul>",
            "<ul><li><p>a</p></li><li><p>b</p></li></ul>",
        ),
        (
            "<ul><li>a</li><ul><li>b</li></ul></ul>",
            "<ul><li><p>a</p><ul><li><p>b</p></li></ul></li></ul>",
        ),
        (
            "<ul><li><ul><li>orphan</li></ul></li></ul>",
            "<ul><li><p>orphan</p></li></ul>",
        ),
        (
            "<ol><li>a<ul><li>b</li></ul>c</li></ol>",
            "<ol><li><p>a</p><ul><li><p>b</p></li></ul></li><li><p>c</p></li></ol>",
        ),
    ],
)
def test_lists_are_brought_into_one_shape(raw: str, expected: str):
    assert sanitize_rich_text(raw) == expected


def test_lists_deeper_than_one_nesting_level_are_flattened():
    raw = (
        "<ul><li>a<ul><li>b<ol><li>c<ul><li>d</li></ul></li></ol></li>"
        "<li>e</li></ul></li><li>f</li></ul>"
    )

    assert sanitize_rich_text(raw) == (
        "<ul><li><p>a</p><ul><li><p>b</p></li><li><p>c</p></li><li><p>d</p></li>"
        "<li><p>e</p></li></ul></li><li><p>f</p></li></ul>"
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("<p>a</p><p></p><p></p><p></p><p>b</p>", "<p>a</p><p></p><p>b</p>"),
        ("<p></p><p>a</p><p></p>", "<p>a</p>"),
        ("<p>a</p><p><br></p><p>&nbsp;</p><p> </p><p>b</p>", "<p>a</p><p></p><p>b</p>"),
        ("<p>a<br><br><br><br><br>b</p>", "<p>a<br><br>b</p>"),
        ("<p><br>a<br></p><p><br><br></p>", "<p>a</p>"),
        ("<p>a<br> <br>\u00a0<br>b</p>", "<p>a<br><br>b</p>"),
        ("<p> <br>a<br> </p>", "<p>a</p>"),
        ("<p>a\n  b\r\nc</p>", "<p>a b c</p>"),
        ("<p>  a  <strong>b </strong> c</p>", "<p>  a  <strong>b </strong> c</p>"),
        (
            "<ul><li>a</li></ul><p></p><p></p><ul><li>b</li></ul>",
            "<ul><li><p>a</p></li></ul><p></p><ul><li><p>b</p></li></ul>",
        ),
    ],
)
def test_spacing_is_limited_to_one_blank_line(raw: str, expected: str):
    assert sanitize_rich_text(raw) == expected


def test_a_description_from_before_lists_is_kept_as_it_was():
    old = (
        "<p><strong>Acme</strong> builds <em>robots</em>.<br>Since 1900.</p>"
        "<p>Join <u>us</u> &amp; <s>them</s>.</p>"
    )

    assert sanitize_rich_text(old) == old


def test_lists_count_their_visible_text_line_by_line():
    html = (
        "<p>Intro</p><ul><li><p>ab</p><ol><li><p>c</p></li></ol></li>"
        "<li><p>d<br>e</p></li></ul>"
    )

    assert rich_text_length(html) == len("Intro\nab\nc\nd\ne")


def test_a_blank_line_counts_as_one_character():
    assert rich_text_length("<p>a</p><p></p><p>b</p>") == len("a\n\nb")


def test_the_count_follows_the_cleaned_description():
    raw = "<p>a</p><p></p><p></p><p></p><p>b<br><br><br>c  d</p>"

    assert rich_text_length(sanitize_rich_text(raw)) == len("a\n\nb\n\nc  d")


def test_plain_text_marks_list_items():
    html = (
        "<p>Intro</p><ul><li><p>a</p></li><li><p>b</p><ul><li><p>c</p></li></ul>"
        "</li></ul><p></p><ol><li><p>x</p><ol><li><p>y</p></li><li><p>z</p></li>"
        "</ol></li><li><p>two<br>lines</p></li></ol>"
    )

    assert rich_text_plain(html) == (
        "Intro\n• a\n• b\n   – c\n\n1. x\n   a. y\n   b. z\n2. two\n   lines"
    )


def test_blocks_describe_lists_and_blank_lines():
    html = (
        "<p>Intro</p><p></p><ol><li><p><strong>a</strong></p>"
        "<ul><li><p>b</p></li></ul></li></ol>"
    )

    def run(text: str, bold: bool = False) -> dict[str, object]:
        return {
            "text": text,
            "bold": bold,
            "italic": False,
            "underline": False,
            "strike": False,
        }

    assert rich_text_blocks(html) == [
        [run("Intro")],
        {"blank": True},
        {
            "ordered": True,
            "items": [
                {
                    "inlines": [run("a", bold=True)],
                    "lists": [
                        {
                            "ordered": False,
                            "items": [{"inlines": [run("b")], "lists": []}],
                        }
                    ],
                }
            ],
        },
    ]


def test_stored_line_breaks_render_as_they_were_saved():
    blocks = rich_text_blocks("<p>a<br><br><br>b  c</p>")

    assert blocks[0] == [
        {
            "text": "a",
            "bold": False,
            "italic": False,
            "underline": False,
            "strike": False,
        },
        {"break": True},
        {"break": True},
        {"break": True},
        {
            "text": "b  c",
            "bold": False,
            "italic": False,
            "underline": False,
            "strike": False,
        },
    ]
