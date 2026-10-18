"""The authentication domain area: identity, secrets, and the proof of both.

Topic 23's subject, split the way it teaches: ``ports.py`` is the whole
vocabulary (the store Protocols — users, sessions, API keys, one-time
codes, refresh families — plus every request and result row, and the
secrets discipline stated once for the area); ``password_service.py``
is argon2 behind one seam (hash, verify, the rehash signal, and the
timing-uniform check every login shares); ``session_service.py`` is the
server-side session with a itsdangerous-sealed cookie;
``api_key_service.py`` is prefix + 256-bit secret, SHA-256 at rest,
constant-time lookup; ``jwt_service.py`` is HS256 mint/verify with every
failure mode classified; ``oauth_service.py`` is the in-repo
authorization server (authorization-code + PKCE S256); and
``refresh_service.py`` is rotating one-time refresh tokens in revocable
families with reuse detection. Everything here is driver-free — argon2,
itsdangerous, and PyJWT vocabulary stays inside the engines, and every
guarantee runs on ordered awaits with no sleeps.
"""

from guide.domain.auth.api_key_service import ApiKeyService
from guide.domain.auth.jwt_service import TokenService
from guide.domain.auth.oauth_service import OAuthProviderService
from guide.domain.auth.password_service import PasswordService
from guide.domain.auth.refresh_service import RefreshRotationService
from guide.domain.auth.session_service import SessionService

__all__ = [
    "ApiKeyService",
    "OAuthProviderService",
    "PasswordService",
    "RefreshRotationService",
    "SessionService",
    "TokenService",
]
