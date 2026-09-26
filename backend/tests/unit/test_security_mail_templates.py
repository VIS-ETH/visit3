import multiprocessing

from app.core.exceptions import MailTemplateInvalid
from app.mail_templates.renderer import render_fragment

NESTED_LOOPS = (
    "{% for a in range(100000) %}{% for b in range(100000) %}{% endfor %}{% endfor %}"
)
RENDER_BUDGET_SECONDS = 3


def _render_nested_loops() -> None:
    try:
        render_fragment(NESTED_LOOPS, {}, "sec", "body_de")
    except MailTemplateInvalid:
        pass


def test_a_staff_template_cannot_render_forever():
    worker = multiprocessing.get_context("fork").Process(target=_render_nested_loops)
    worker.start()
    worker.join(RENDER_BUDGET_SECONDS)
    still_rendering = worker.is_alive()
    worker.kill()
    worker.join()

    assert not still_rendering
