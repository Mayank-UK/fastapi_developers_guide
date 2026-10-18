"""The OAuth demo payload: the flow's map, derived purely.

``GET /api/demo/auth/oauth`` serves this payload — topic 23's fifth
demo (``auth:oauth``), inline in the OAuth2 section. The panel carries
the registered client, the exact four steps of the code+PKCE grant as
this guide implements them, and the endpoints of each step.
"""

from guide.core.serialization import CamelModel

FLOW_STEPS: tuple[str, ...] = (
    "PKCE pair — the client generates verifier + S256 challenge locally; the "
    "verifier never leaves the client until step three",
    "authorize — the client sends client_id, its registered redirect_uri, state, "
    "and the challenge; the user consents; the server answers the redirect with a "
    "one-time code",
    "token — the client presents code + verifier + the SAME redirect_uri over the "
    "back channel; S256(verifier) must match the challenge in constant time",
    "use — the exchanged access token rides Authorization: Bearer against the "
    "protected resource and verifies like any JWT",
)
"""The grant as this guide implements it — panel and prose share it."""


class OAuthPanelPayload(CamelModel):
    """Wire shape of ``GET /api/demo/auth/oauth`` — the flow's map."""

    client_id: str
    client_kind: str
    redirect_uris: list[str]
    client_scopes: list[str]
    code_ttl_seconds: int
    pkce_note: str
    steps: list[str]
    pkce_endpoint: str
    authorize_endpoint: str
    token_endpoint: str
    protected_endpoint: str
    reasoning: str


def build_oauth_panel_payload(
    *,
    client_id: str,
    client_kind: str,
    redirect_uris: list[str],
    client_scopes: list[str],
    code_ttl_seconds: int,
    pkce_note: str,
    pkce_endpoint: str,
    authorize_endpoint: str,
    token_endpoint: str,
    protected_endpoint: str,
) -> OAuthPanelPayload:
    """Shape the map (pure) — the registered client and its four steps."""
    reasoning = (
        f"This server has exactly one registered client — {client_id} ({client_kind}): "
        "no client secret exists to leak, because PKCE replaces it. Walk the steps "
        "in order: generate the pair, authorize (consent is simulated for the "
        "seeded user ada; the redirect the client would follow is shown), then "
        "exchange — and try the exchange with a WRONG verifier to watch the "
        f"one-time code die in the attempt. Codes live {code_ttl_seconds}s and one "
        "presentation; the access token they buy is a JWT with "
        f"{', '.join(client_scopes)}."
    )
    return OAuthPanelPayload(
        client_id=client_id,
        client_kind=client_kind,
        redirect_uris=redirect_uris,
        client_scopes=client_scopes,
        code_ttl_seconds=code_ttl_seconds,
        pkce_note=pkce_note,
        steps=list(FLOW_STEPS),
        pkce_endpoint=pkce_endpoint,
        authorize_endpoint=authorize_endpoint,
        token_endpoint=token_endpoint,
        protected_endpoint=protected_endpoint,
        reasoning=reasoning,
    )
