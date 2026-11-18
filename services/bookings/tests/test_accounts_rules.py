from accounts import rules


def test_valid_registration_has_no_errors():
    assert rules.validate_registration("ana_padel", "smash2026", username_taken=False) == []


def test_too_short_username_is_rejected():
    errors = rules.validate_registration("an", "smash2026", username_taken=False)
    assert "Username must be 3-20 characters: letters, numbers or underscores." in errors


def test_username_with_spaces_is_rejected():
    errors = rules.validate_registration("ana padel", "smash2026", username_taken=False)
    assert "Username must be 3-20 characters: letters, numbers or underscores." in errors


def test_taken_username_is_rejected():
    errors = rules.validate_registration("ana", "smash2026", username_taken=True)
    assert "That username is already taken." in errors


def test_short_password_is_rejected():
    errors = rules.validate_registration("ana", "abc12", username_taken=False)
    assert "Password must be at least 8 characters." in errors


def test_password_without_numbers_is_rejected():
    errors = rules.validate_registration("ana", "onlyletters", username_taken=False)
    assert "Password must contain both letters and numbers." in errors
