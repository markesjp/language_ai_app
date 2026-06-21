from app.models import User
from app.services.admin_auth import create_password_record
from app.services.user_auth import create_oauth_state, create_user_session_token, verify_oauth_state, verify_user_session_token


def test_user_session_token_roundtrip():
    password_hash, salt, iterations = create_password_record("secret123")
    user = User(
        id="user-1",
        email="learner@example.com",
        display_name="Learner",
        password_hash=password_hash,
        salt=salt,
        iterations=iterations,
    )

    token = create_user_session_token(user)
    session = verify_user_session_token(token)

    assert session is not None
    assert session.user_id == "user-1"
    assert session.email == "learner@example.com"


def test_user_session_rejects_tampered_token():
    user = User(id="user-1", email="learner@example.com", display_name="Learner")
    token = create_user_session_token(user)

    assert verify_user_session_token(f"{token}x") is None


def test_google_oauth_state_roundtrip():
    state = create_oauth_state()

    assert verify_oauth_state(state)
    assert not verify_oauth_state(f"{state}x")
