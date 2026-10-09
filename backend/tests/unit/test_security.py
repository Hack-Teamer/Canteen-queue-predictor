from datetime import timedelta
import pytest
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


def test_password_hashing():
    pwd = "studentpassword123"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_jwt_tokens():
    payload = {"sub": "user-uuid-123", "email": "test@test.com", "role": "student"}
    access_token = create_access_token(payload)
    decoded = decode_token(access_token)
    assert decoded["sub"] == "user-uuid-123"
    assert decoded["type"] == "access"

    refresh_token = create_refresh_token(payload)
    decoded_rf = decode_token(refresh_token)
    assert decoded_rf["sub"] == "user-uuid-123"
    assert decoded_rf["type"] == "refresh"


def test_expired_token():
    payload = {"sub": "user-uuid-123", "email": "test@test.com", "role": "student"}
    expired_token = create_access_token(payload, expires_delta=timedelta(seconds=-10))
    with pytest.raises(UnauthorizedError):
        decode_token(expired_token)
