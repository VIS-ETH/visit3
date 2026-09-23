from sqlmodel import col, select

from app.core.deleted_filter import include_deleted
from app.models.company import Company
from app.models.user import User, UserRole
from app.schemas.user import (
    UpdateCompanyUserInput,
    UpdateUserProfileInput,
    UserFilter,
)


async def test_create_user_normalizes_email_and_strips_names(user_repository):
    user = await user_repository.create_user(
        User(
            email="  Ada@Example.COM ",
            password="hash",
            first_name="  Ada  ",
            last_name="  Lovelace  ",
        )
    )

    assert user.email == "ada@example.com"
    assert user.first_name == "Ada"
    assert user.last_name == "Lovelace"


async def test_get_by_email_normalizes_lookup(user_repository):
    user = await user_repository.create_user(
        User(email="ada@example.com", password="hash")
    )

    result = await user_repository.get_by_email("  ADA@EXAMPLE.COM ")

    assert result == user


async def test_deleted_user_is_hidden_by_default(user_repository, db_session):
    user = await user_repository.create_user(
        User(email="delete-me@example.com", password="hash")
    )

    await user_repository.delete_user(user)

    assert await user_repository.get_by_id(user.id) is None
    result = await db_session.execute(include_deleted(select(User)))
    deleted_users = result.scalars().all()
    assert [deleted_user.email for deleted_user in deleted_users] == [
        "delete-me@example.com"
    ]
    assert deleted_users[0].deleted_at is not None


async def _stored_password(db_session, user_id):
    result = await db_session.execute(
        include_deleted(select(col(User.password)).where(col(User.id) == user_id))
    )
    return result.scalar_one()


async def test_update_password_skips_deleted_users(user_repository, db_session):
    user = await user_repository.create_user(
        User(email="deleted@example.com", password="old-hash")
    )
    await user_repository.delete_user(user)

    await user_repository.update_password(user.id, "new-hash")

    assert await _stored_password(db_session, user.id) == "old-hash"


async def test_update_password_updates_active_users(user_repository, db_session):
    user = await user_repository.create_user(
        User(email="active@example.com", password="old-hash")
    )

    await user_repository.update_password(user.id, "new-hash")

    assert await _stored_password(db_session, user.id) == "new-hash"


async def test_load_user_roles_loads_assigned_roles(
    user_repository,
    role_repository,
    db_session,
):
    user = await user_repository.create_user(
        User(email="role-user@example.com", password="hash")
    )
    admin_role = await role_repository.get_or_create("admin")
    active_role = await role_repository.get_or_create("vis-active")
    db_session.add(UserRole(user_id=user.id, role_id=admin_role.id))
    db_session.add(UserRole(user_id=user.id, role_id=active_role.id))
    await db_session.commit()

    result = await user_repository.load_user_roles(user)

    assert {role.name for role in result.roles} == {"admin", "vis-active"}


async def test_confirm_email_sets_email_confirmed(user_repository):
    user = await user_repository.create_user(
        User(email="confirm@example.com", password="hash", email_confirmed=False)
    )

    await user_repository.confirm_email(user)
    refreshed = await user_repository.get_by_id(user.id)

    assert refreshed is not None
    assert refreshed.email_confirmed is True


async def test_update_user_updates_fields_and_company(
    user_repository,
    company_repository,
):
    company = await company_repository.create_company("Acme AG")
    user = await user_repository.create_user(
        User(email="profile@example.com", password="hash")
    )

    result = await user_repository.update_user(
        user,
        UpdateCompanyUserInput(
            email="updated@example.com",
            first_name="Ada",
            last_name="Lovelace",
            phone_number="+41791234567",
            company_id=company.id,
        ),
    )

    assert result.email == "updated@example.com"
    assert result.first_name == "Ada"
    assert result.last_name == "Lovelace"
    assert result.phone_number == "+41791234567"
    assert result.company_id == company.id


async def test_update_user_unconfirms_changed_email(user_repository):
    user = await user_repository.create_user(
        User(email="old@example.com", password="hash", email_confirmed=True)
    )

    result = await user_repository.update_user(
        user, UpdateCompanyUserInput(email="new@example.com")
    )

    assert result.email == "new@example.com"
    assert result.email_confirmed is False


async def test_update_user_keeps_email_confirmed_when_email_unchanged(
    user_repository,
):
    user = await user_repository.create_user(
        User(email="same@example.com", password="hash", email_confirmed=True)
    )

    result = await user_repository.update_user(
        user, UpdateCompanyUserInput(email="  Same@Example.COM ", first_name="Ada")
    )

    assert result.first_name == "Ada"
    assert result.email_confirmed is True


async def test_update_user_clears_only_explicitly_sent_fields(user_repository):
    user = await user_repository.create_user(
        User(
            email="fields@example.com",
            password="hash",
            first_name="Ada",
            last_name="Lovelace",
            phone_number="+41791234567",
        )
    )

    result = await user_repository.update_user(
        user, UpdateUserProfileInput(phone_number=None)
    )

    assert result.phone_number is None
    assert result.first_name == "Ada"
    assert result.last_name == "Lovelace"


async def test_search_users_excludes_deleted_users(user_repository):
    kept = await user_repository.create_user(
        User(email="kept@example.com", password="hash")
    )
    gone = await user_repository.create_user(
        User(email="gone@example.com", password="hash")
    )
    await user_repository.delete_user(gone)

    found = await user_repository.search_users(None, UserFilter.ALL, 0, 10)
    total = await user_repository.count_users_matching(None, UserFilter.ALL)

    assert [user.email for user in found] == [kept.email]
    assert total == 1


async def test_search_users_matches_the_company_name(user_repository, db_session):
    company = Company(name="Fancy Robotics AG")
    db_session.add(company)
    await db_session.commit()
    await user_repository.create_user(
        User(email="member@example.com", password="hash", company_id=company.id)
    )
    await user_repository.create_user(
        User(email="outsider@example.com", password="hash")
    )

    found = await user_repository.search_users("robotics", UserFilter.ALL, 0, 10)

    assert [user.email for user in found] == ["member@example.com"]


async def test_search_users_pages_alphabetically(user_repository):
    for email in ["c@example.com", "a@example.com", "b@example.com"]:
        await user_repository.create_user(User(email=email, password="hash"))

    first = await user_repository.search_users(None, UserFilter.ALL, 0, 2)
    second = await user_repository.search_users(None, UserFilter.ALL, 2, 2)

    assert [user.email for user in first] == ["a@example.com", "b@example.com"]
    assert [user.email for user in second] == ["c@example.com"]


async def test_clear_pending_invite_forgets_the_token(user_repository):
    user = await user_repository.create_user(
        User(email="invited@example.com", password="hash", pending_invite_token="tok")
    )

    await user_repository.clear_pending_invite(user)

    reloaded = await user_repository.get_by_id(user.id)
    assert reloaded is not None
    assert reloaded.pending_invite_token is None
