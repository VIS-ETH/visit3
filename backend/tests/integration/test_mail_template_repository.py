from app.mail_templates.keys import MailTemplateKey
from app.mail_templates.texts import MailTemplateTexts

TEXTS = MailTemplateTexts(
    subject_de="Betreff",
    subject_en="Subject",
    body_de="<p>Hallo</p>",
    body_en="<p>Hello</p>",
)
CHANGED = MailTemplateTexts(
    subject_de="Neuer Betreff",
    subject_en="New subject",
    body_de="<p>Neu</p>",
    body_en="<p>New</p>",
)


async def test_upsert_creates_and_then_updates_the_same_row(
    user_repository, mail_template_repository
):
    author = await user_repository.create_user(
        user_repository.model(email="author@example.com", password="hash")
    )
    key = str(MailTemplateKey.PASSWORD_RESET)

    created = await mail_template_repository.upsert(key, TEXTS, author.id)
    updated = await mail_template_repository.upsert(key, CHANGED, author.id)

    assert created.id == updated.id
    assert updated.subject_de == "Neuer Betreff"
    assert updated.updated_by_user_id == author.id
    assert len(await mail_template_repository.list_templates()) == 1


async def test_templates_are_listed_by_key(user_repository, mail_template_repository):
    author = await user_repository.create_user(
        user_repository.model(email="lister@example.com", password="hash")
    )
    await mail_template_repository.upsert(
        str(MailTemplateKey.PASSWORD_RESET), TEXTS, author.id
    )
    await mail_template_repository.upsert(
        str(MailTemplateKey.COMPANY_INVITE), TEXTS, author.id
    )

    keys = [
        template.key for template in await mail_template_repository.list_templates()
    ]

    assert keys == sorted(keys)


async def test_unknown_key_has_no_row(mail_template_repository):
    assert await mail_template_repository.get_by_key("does_not_exist") is None


async def test_delete_by_key_removes_the_row_and_allows_a_new_one(
    user_repository, mail_template_repository
):
    author = await user_repository.create_user(
        user_repository.model(email="resetter@example.com", password="hash")
    )
    key = str(MailTemplateKey.PASSWORD_RESET)
    await mail_template_repository.upsert(key, TEXTS, author.id)

    await mail_template_repository.delete_by_key(key)
    recreated = await mail_template_repository.upsert(key, CHANGED, author.id)

    assert await mail_template_repository.list_templates() == [recreated]


async def test_delete_by_key_is_a_no_op_for_an_unstored_key(mail_template_repository):
    await mail_template_repository.delete_by_key(str(MailTemplateKey.COMPANY_INVITE))

    assert await mail_template_repository.list_templates() == []
