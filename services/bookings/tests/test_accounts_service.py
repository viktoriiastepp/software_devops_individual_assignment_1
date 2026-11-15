from accounts import repository, service


def test_register_stores_a_hash_not_the_password(temp_db):
    user_id, errors = service.register("Ana", "smash2026")
    assert errors == []
    user = repository.get_user(user_id)
    assert user["username"] == "ana"
    assert user["password_hash"] != "smash2026"


def test_same_username_cannot_register_twice(temp_db):
    service.register("ana", "smash2026")
    user_id, errors = service.register("ANA", "volley2026")
    assert user_id is None
    assert "That username is already taken." in errors


def test_login_works_with_correct_password(temp_db):
    service.register("ana", "smash2026")
    assert service.authenticate(" Ana ", "smash2026")["username"] == "ana"


def test_login_fails_with_wrong_password(temp_db):
    service.register("ana", "smash2026")
    assert service.authenticate("ana", "wrong2026") is None


def test_login_fails_for_unknown_user(temp_db):
    assert service.authenticate("nobody", "smash2026") is None
