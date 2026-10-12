"""
Sign in with ChatGPT: the models can be used with the ChatGPT plan of a connected account instead of
an API key, see https://developers.openai.com/siwc/token-sharing-open-source.

The OAuth callback can only be a loopback address, which is the machine of the browser and not this
server, so the user copies the address of the callback page that fails to load back to the webapp.
The code in it is useless without the PKCE verifier, which never leaves the server.
"""
from datetime import datetime, timezone
from threading import Lock
from time import sleep, time
from typing import Optional
from urllib.parse import parse_qs, quote, urlencode, urlparse
import base64
import hashlib
import json
import os
import secrets
import uuid
import jwt
import requests

ISSUER = "https://auth.openai.com"
AUTHORIZE_URL = f"{ISSUER}/api/accounts/authorize"
TOKEN_URL = f"{ISSUER}/api/accounts/oauth/token"
REVOKE_URL = f"{ISSUER}/api/accounts/oauth/revoke"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"
API_URL = "https://api.openai.com/v1"
# Port 1455 is required for the first registration, and nothing listens on it anyway.
REDIRECT_URI = "http://127.0.0.1:1455/auth/callback"
PLAN_SCOPE = "chatgpt.tokens.use.direct"
SCOPES = f"openid profile email offline_access resource.invoke {PLAN_SCOPE}"
USAGE_SETTINGS_URL = "https://chatgpt.com/settings/usage"
APP_NAME = "Sajtóadatbázis automat"
AUTH_FILE = "data/chatgpt_auth.json"
LOGIN_TIMEOUT = 15 * 60
MODELS_CACHE_TIME = 60 * 60
# The refresh token can not be used any more, the user has to sign in again.
TERMINAL_REFRESH_ERRORS = {
    "invalid_grant",
    "invalid_refresh_token",
    "token_expired",
    "refresh_token_expired",
    "refresh_token_invalidated",
    "refresh_token_reused",
}
TOKEN_FIELDS = ("id_token", "access_token", "refresh_token", "token_type", "expires_at", "scopes")


class ChatGPTUnavailable(Exception):
    """The plan can not be used now, but it is not the fault of the request, so it can wait."""

    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


class LoginError(Exception):
    pass


class TokenError(Exception):
    def __init__(self, status: int, error: str, description: str):
        super().__init__(f"{status} {error}: {description}")
        self.status = status
        self.error = error


# The refresh token rotates, so the refreshes must not race.
_lock = Lock()
_pending_logins: dict[str, dict] = {}
_jwks = jwt.PyJWKClient(JWKS_URL)
# Why the plan could not be used last time, shown on the UI until it works again.
_problem: Optional[dict] = None
_models_cache: Optional[dict] = None


def _load() -> dict:
    try:
        with open(AUTH_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save(state: dict) -> None:
    """Written atomically and only readable by the owner, as it holds the tokens."""
    tmp = f"{AUTH_FILE}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, AUTH_FILE)


def _set_problem(message: Optional[str]) -> None:
    global _problem
    _problem = {"message": message, "time": int(time())} if message else None


def _unavailable(message: str, retry_after: int) -> ChatGPTUnavailable:
    _set_problem(message)
    return ChatGPTUnavailable(message, retry_after)


def _store_tokens(state: dict, tokens: dict) -> None:
    state["access_token"] = tokens["access_token"]
    # A refresh may keep the previous refresh token, ID token and scopes.
    state["refresh_token"] = tokens.get("refresh_token") or state.get("refresh_token")
    state["id_token"] = tokens.get("id_token") or state.get("id_token")
    if tokens.get("scope"):
        state["scopes"] = tokens["scope"].split()
    state["token_type"] = tokens.get("token_type", "Bearer")
    state["expires_at"] = int(time()) + int(tokens.get("expires_in", 3600))
    state["saved_at"] = datetime.now(timezone.utc).isoformat()


def _token_request(data: dict) -> dict:
    try:
        response = requests.post(TOKEN_URL, data=data, timeout=30)
    except requests.RequestException as e:
        raise TokenError(0, "network_error", str(e))
    if response.ok:
        return response.json()
    try:
        body = response.json()
    except ValueError:
        body = {}
    error = body.get("error")
    # Not every error is in the OAuth format.
    if isinstance(error, dict):
        error, description = error.get("code") or error.get("type"), error.get("message")
    else:
        description = body.get("error_description") or response.text[:500]
    raise TokenError(response.status_code, error or "unknown_error", description or "")


def status() -> dict:
    state = _load()
    return {
        "connected": bool(state.get("refresh_token")),
        "plan_usage": PLAN_SCOPE in state.get("scopes", []),
        # The email of the previous sign-in is kept after signing out, for signing in again.
        "email": state.get("email"),
        "name": state.get("name"),
        "registered": bool(state.get("client_id")),
        "problem": _problem,
        "usage_url": USAGE_SETTINGS_URL,
    }


def start_login(new_account: bool) -> str:
    """
    Args:
        new_account: Registers a new client, which is needed for signing in with another account,
            as a client is bound to the account it was registered with.

    Returns:
        The authorization URL to open in the browser.
    """
    with _lock:
        state = _load()
        if not state.get("ext_agent_host_id"):
            state["ext_agent_host_id"] = f"urn:uuid:{uuid.uuid4()}"
            _save(state)

    reuse = bool(state.get("client_id")) and not new_account
    verifier = secrets.token_urlsafe(64)
    login = {
        "state": secrets.token_urlsafe(32),
        "nonce": secrets.token_urlsafe(32),
        "verifier": verifier,
        "client_id": state["client_id"] if reuse else None,
        "created": time(),
    }
    params = {
        "client_id": login["client_id"] or "dynamic_agent_client",
        "ext_agent_host_id": state["ext_agent_host_id"],
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "resource": API_URL,
        "state": login["state"],
        "nonce": login["nonce"],
        "code_challenge_method": "S256",
        "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode(),
    }
    if reuse:
        if state.get("id_token"):
            params["id_token_hint"] = state["id_token"]
        if state.get("email"):
            params["login_hint"] = state["email"]
    else:
        params["agent_name_hint"] = APP_NAME

    for key in [k for k, v in _pending_logins.items() if time() - v["created"] > LOGIN_TIMEOUT]:
        del _pending_logins[key]
    _pending_logins[login["state"]] = login
    return f"{AUTHORIZE_URL}?{urlencode(params, quote_via=quote)}"


def _validate_id_token(id_token: str, client_id: str, nonce: str) -> dict:
    try:
        key = _jwks.get_signing_key_from_jwt(id_token).key
        claims = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=ISSUER,
            leeway=60,
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as e:
        raise LoginError(f"Érvénytelen azonosító token: {e}")
    if claims.get("nonce") != nonce:
        raise LoginError("Érvénytelen azonosító token: nem egyezik a nonce.")
    return claims


def finish_login(callback_url: str) -> None:
    """
    Args:
        callback_url: The address of the callback page, where the browser was redirected.
    """
    query = parse_qs(urlparse(callback_url.strip()).query)

    def param(name: str) -> Optional[str]:
        return (query.get(name) or [None])[0]

    login = _pending_logins.get(param("state") or "")
    if login is None or time() - login["created"] > LOGIN_TIMEOUT:
        raise LoginError(
            "Ismeretlen vagy lejárt bejelentkezés. Az átirányítás utáni címet másold be "
            "(http://127.0.0.1:1455/auth/callback?...), vagy kezdd újra a bejelentkezést!"
        )
    # The authorization URL has the same state, it is not used up if that is pasted by mistake.
    if not param("code") and not param("error"):
        raise LoginError("Nincs kód a bemásolt címben, az átirányítás utáni címet másold be!")
    del _pending_logins[login["state"]]
    if param("error") == "access_denied":
        raise LoginError("A bejelentkezést megszakítottad vagy elutasítottad.")
    if param("error"):
        raise LoginError(f"Sikertelen bejelentkezés: {param('error')} {param('error_description') or ''}")

    returned_client_id = param("client_id")
    if login["client_id"]:
        if returned_client_id and returned_client_id != login["client_id"]:
            raise LoginError("A bejelentkezés más klienshez tartozik, kezdd újra!")
        client_id = login["client_id"]
    elif not returned_client_id or returned_client_id == "dynamic_agent_client":
        raise LoginError("Nem fejeződött be a regisztráció (nincs client_id a címben), kezdd újra!")
    else:
        client_id = returned_client_id

    try:
        tokens = _token_request(
            {
                "grant_type": "authorization_code",
                "client_id": client_id,
                "code": param("code"),
                "code_verifier": login["verifier"],
                "redirect_uri": REDIRECT_URI,
                "resource": API_URL,
            }
        )
    except TokenError as e:
        raise LoginError(f"Nem sikerült a bejelentkezés, kezdd újra! ({e})")
    claims = _validate_id_token(tokens.get("id_token", ""), client_id, login["nonce"])

    global _models_cache
    with _lock:
        state = _load()
        if login["client_id"] and state.get("subject") and claims["sub"] != state["subject"]:
            raise LoginError(
                f"Ez nem a korábban csatlakoztatott fiók ({state.get('email')}). "
                "Másik fiókhoz a „Másik fiókkal” gombot használd!"
            )
        state.update(
            {
                "issuer": ISSUER,
                "client_id": client_id,
                "subject": claims["sub"],
                "email": claims.get("email"),
                "name": claims.get("name"),
            }
        )
        state["scopes"] = []
        _store_tokens(state, tokens)
        _save(state)
        _models_cache = None
    _set_problem(None)


def logout() -> bool:
    """
    Revokes the session and forgets the tokens, but the client registration is kept for signing in
    again.

    Returns:
        Whether the revocation was confirmed, the app can still be disconnected in ChatGPT otherwise.
    """
    global _models_cache
    with _lock:
        state = _load()
        revoked = not state.get("refresh_token")
        # Network errors and 5xx are retried, an empty 200 is a success even for an invalid token.
        for attempt in range(0 if revoked else 3):
            if attempt:
                sleep(2**attempt)
            try:
                response = requests.post(
                    REVOKE_URL,
                    data={
                        "token": state["refresh_token"],
                        "token_type_hint": "refresh_token",
                        "client_id": state["client_id"],
                    },
                    timeout=30,
                )
                revoked = response.status_code == 200
                if response.status_code < 500:
                    break
            except requests.RequestException:
                pass
        for key in TOKEN_FIELDS:
            state.pop(key, None)
        _save(state)
        _models_cache = None
    _set_problem(None)
    return revoked


def _access_token(force_refresh: bool = False) -> str:
    with _lock:
        state = _load()
        if not state.get("refresh_token"):
            raise ChatGPTUnavailable("Nincs csatlakoztatott ChatGPT fiók.", 60)
        if PLAN_SCOPE not in state.get("scopes", []):
            raise ChatGPTUnavailable("A ChatGPT fióknál nincs engedélyezve az előfizetés használata.", 60)
        if not force_refresh and state.get("expires_at", 0) - 300 > time():
            return state["access_token"]

        try:
            tokens = _token_request(
                {
                    "grant_type": "refresh_token",
                    "client_id": state["client_id"],
                    "refresh_token": state["refresh_token"],
                    "resource": API_URL,
                }
            )
        except TokenError as e:
            if e.error in TERMINAL_REFRESH_ERRORS:
                # E.g. disconnected in the ChatGPT settings. The ID token is kept as a hint for
                # signing in again.
                for key in ("access_token", "refresh_token", "expires_at"):
                    state.pop(key, None)
                _save(state)
                raise _unavailable(
                    f"Megszűnt a ChatGPT kapcsolat (pl. leválasztották a ChatGPT beállításaiban), "
                    f"jelentkezz be újra! ({e})",
                    60,
                )
            if e.status == 0 or e.status >= 500:
                raise _unavailable(f"Nem sikerült megújítani a ChatGPT tokent: {e}", 120)
            raise ValueError(f"Nem sikerült megújítani a ChatGPT tokent: {e}")
        _store_tokens(state, tokens)
        _save(state)
        return state["access_token"]


def _raise_error(error: dict, status: Optional[int] = None, request_id: Optional[str] = None):
    code = error.get("code")
    message = f"{status or ''} {code or ''}: {error.get('message') or ''}".strip()
    if request_id:
        message += f" (request id: {request_id})"
    if code == "subscription_sharing_usage_limit_exceeded" or status == 429:
        raise _unavailable(
            "Elfogyott a ChatGPT-előfizetés vagy az ennek az alkalmazásnak beállított keret, a "
            f"generálás szünetel. A keret a ChatGPT beállításaiban kezelhető. ({message})",
            15 * 60,
        )
    if code in ("subscription_sharing_usage_unavailable", "subscription_sharing_user_unavailable") or status == 503:
        raise _unavailable(f"A ChatGPT-előfizetés átmenetileg nem használható. ({message})", 5 * 60)
    if code == "subscription_sharing_unsupported_capability":
        raise ValueError(
            f"A ChatGPT-előfizetéssel nem használható funkció: {error.get('param')}. Ha ez a webes "
            f"keresés, állítsd be: DESCRIPTION_CHATGPT_WEB_SEARCH=false. ({message})"
        )
    if code == "subscription_sharing_user_not_eligible":
        raise ValueError(f"A ChatGPT fiók előfizetése nem használható más alkalmazásokban. ({message})")
    raise ValueError(f"Hiba a ChatGPT-től: {message}")


def _api(method: str, path: str, **kwargs) -> requests.Response:
    """Calls the API with the access token, which is refreshed once if it is rejected."""
    for attempt in range(2):
        token = _access_token(force_refresh=attempt > 0)
        try:
            response = requests.request(
                method, f"{API_URL}{path}", headers={"Authorization": f"Bearer {token}"}, **kwargs
            )
        except requests.RequestException as e:
            raise _unavailable(f"Nem érhető el az OpenAI API: {e}", 120)
        if response.status_code != 401 or attempt:
            break
        response.close()

    if not response.ok:
        try:
            body = response.json()
        except ValueError:
            body = {}
        # Requests rejected before reaching the model have a detail instead of an error.
        error = body.get("error")
        if not isinstance(error, dict):
            error = {"message": str(body.get("detail") or response.text[:500])}
        response.close()
        _raise_error(error, response.status_code, response.headers.get("x-request-id"))
    return response


def list_models() -> list[dict]:
    """The models the account can use, the default first."""
    global _models_cache
    state = _load()
    if (
        _models_cache is None
        or _models_cache["client_id"] != state.get("client_id")
        or time() - _models_cache["time"] > MODELS_CACHE_TIME
    ):
        data = _api("GET", "/models", timeout=30).json()
        models = [
            {"slug": m["slug"], "display_name": m.get("display_name") or m["slug"]}
            for m in data.get("models") or []
            if m.get("visibility") == "list" and m.get("slug")
        ]
        _models_cache = {"client_id": state.get("client_id"), "time": time(), "models": models}
    return _models_cache["models"]


def default_model() -> str:
    models = list_models()
    if not models:
        raise ValueError("A ChatGPT fiókhoz nem tartozik használható modell.")
    return models[0]["slug"]


def create_response(body: dict) -> dict:
    """
    Sends a Responses API request with the plan, which has to be streamed and can not be stored.
    See https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations for the
    parameters that are not supported.

    Returns:
        The completed response object.
    """
    response = _api(
        "POST", "/responses", json={**body, "store": False, "stream": True}, stream=True, timeout=(30, 600)
    )
    # As the response is not stored, the completed response has an empty output, the output items
    # are only sent one by one.
    output: list[dict] = []
    with response:
        # Without a charset in the content type, requests would decode it as Latin-1.
        response.encoding = "utf-8"
        request_id = response.headers.get("x-request-id")
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:") or line[5:].strip() == "[DONE]":
                continue
            event = json.loads(line[5:])
            if event.get("type") == "response.output_item.done" and event.get("item"):
                output.append(event["item"])
            if event.get("type") == "response.completed":
                _set_problem(None)
                completed = event["response"]
                if not completed.get("output"):
                    completed["output"] = output
                return completed
            if event.get("type") == "response.failed":
                _raise_error((event.get("response") or {}).get("error") or {}, None, request_id)
            if event.get("type") == "response.incomplete":
                details = (event.get("response") or {}).get("incomplete_details") or {}
                raise ValueError(f"Nem teljes válasz a ChatGPT-től: {details.get('reason')}")
            if event.get("type") == "error":
                _raise_error(event.get("error") or event, None, request_id)
    raise ValueError("Megszakadt a ChatGPT válasza, mielőtt elkészült volna.")
