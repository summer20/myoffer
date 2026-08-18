import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

PUBLIC_PATHS = {"/login", "/health"}
PUBLIC_PREFIXES = ("/static/",)


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)


def check_credentials(username: str, password: str, expected_username: str, expected_password: str) -> bool:
    return secrets.compare_digest(username.encode(), expected_username.encode()) and secrets.compare_digest(
        password.encode(), expected_password.encode()
    )


class LoginRequiredMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if is_public_path(request.url.path):
            return await call_next(request)
        if not request.session.get("logged_in"):
            return RedirectResponse(url="/login", status_code=303)
        return await call_next(request)
