from datetime import timedelta
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification():
    raw_password = "SuperSecretPassword123!"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert hashed.startswith("$2b$")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_token_creation_and_decoding():
    subject = "user-uuid-12345"
    token = create_access_token(
        subject=subject,
        expires_delta=timedelta(minutes=15),
        extra_claims={"role": "admin", "email": "admin@example.com"},
    )

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == subject
    assert payload["role"] == "admin"
    assert payload["email"] == "admin@example.com"
    assert "exp" in payload


def test_token_expiration():
    subject = "expired-user"
    # Token that expired 5 minutes ago
    token = create_access_token(
        subject=subject,
        expires_delta=timedelta(minutes=-5),
    )

    payload = decode_token(token)
    assert payload is None
