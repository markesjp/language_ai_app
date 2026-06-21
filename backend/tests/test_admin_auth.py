from app.models import AdminCredential
from app.services.admin_auth import create_password_record, create_session_token, verify_password, verify_session_token


def test_admin_password_hash_verifies_only_matching_password():
    password_hash, salt, iterations = create_password_record("secret")
    credential = AdminCredential(password_hash=password_hash, salt=salt, iterations=iterations)

    assert verify_password("secret", credential)
    assert not verify_password("wrong", credential)


def test_admin_session_token_roundtrip():
    token = create_session_token()
    session = verify_session_token(token)

    assert session is not None
    assert session.subject == "admin"


def test_admin_session_rejects_tampered_token():
    token = create_session_token()
    tampered = f"{token}x"

    assert verify_session_token(tampered) is None
