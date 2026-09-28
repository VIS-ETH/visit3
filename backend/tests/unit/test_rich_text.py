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
        ("<ul><li>one</li><li>two</li></ul>", "<p>one</p><p>two</p>"),
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
