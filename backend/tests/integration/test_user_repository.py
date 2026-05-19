from sqlmodel import select

from app.core.deleted_filter import include_deleted
from app.models.user import User, UserRole


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


async def test_update_company_user_updates_fields_and_company(
    user_repository,
    company_repository,
):
    company = await company_repository.create_company("Acme AG")
    user = await user_repository.create_user(
        User(email="profile@example.com", password="hash")
    )

    result = await user_repository.update_company_user(
        user,
        email="updated@example.com",
        first_name="Ada",
        last_name="Lovelace",
        phone_number="+41791234567",
        company_id=company.id,
    )

    assert result.email == "updated@example.com"
    assert result.first_name == "Ada"
    assert result.last_name == "Lovelace"
    assert result.phone_number == "+41791234567"
    assert result.company_id == company.id
