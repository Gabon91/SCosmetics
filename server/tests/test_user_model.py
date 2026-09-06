from app.models.user import User, UserRole


def test_user_roles_match_the_project_permissions() -> None:
    assert {role.value for role in UserRole} == {
        "customer",
        "beautician",
        "admin",
    }


def test_user_model_uses_users_table() -> None:
    assert User.__tablename__ == "users"
    assert User.__table__.c.email.unique is True
