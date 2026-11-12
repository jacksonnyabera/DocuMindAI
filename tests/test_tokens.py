import uuid

import pytest

from app.core.tokens import (
    create_access_token,
    decode_access_token,
)


def test_create_and_decode_access_token():
    user_id = uuid.uuid4()
    organization_id = uuid.uuid4()

    token = create_access_token(user_id, organization_id)
    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["org"] == str(organization_id)


def test_invalid_token_is_rejected():
    with pytest.raises(ValueError):
        decode_access_token("not-a-valid-token")


def test_token_signed_with_wrong_secret_is_rejected(monkeypatch):
    user_id = uuid.uuid4()
    organization_id = uuid.uuid4()

    token = create_access_token(user_id, organization_id)

    monkeypatch.setattr(
        "app.core.tokens.settings.secret_key",
        "a-different-secret-key",
    )

    with pytest.raises(ValueError):
        decode_access_token(token)


def test_token_with_invalid_uuid_claims_is_rejected():
    import jwt
    from app.core.config import settings

    token = jwt.encode(
        {
            "sub": "not-a-uuid",
            "org": str(uuid.uuid4()),
            "exp": 4102444800,
            "iat": 1760000000,
        },
        settings.secret_key,
        algorithm="HS256",
    )

    with pytest.raises(ValueError):
        decode_access_token(token)
