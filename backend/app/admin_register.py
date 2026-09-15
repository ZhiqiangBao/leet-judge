"""Loopback-only admin signup. Bound to 127.0.0.1, never shares PORT 8080."""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from .config import ADMIN_REGISTER_PORT, PORT
from .db import get_db
from .deps import create_user
from .schemas import RegisterIn, UserOut

app = FastAPI(title="Local Leet admin register", docs_url=None, redoc_url=None)

_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>注册管理员</title>
<style>
  body { font-family: sans-serif; max-width: 28rem; margin: 12vh auto; padding: 0 1rem; color: #1a1a1a; }
  h1 { font-size: 1.25rem; }
  p { color: #555; line-height: 1.5; }
  label { display: block; margin: 0.75rem 0 0.25rem; }
  input { width: 100%; box-sizing: border-box; padding: 0.45rem 0.5rem; }
  button { margin-top: 1rem; padding: 0.45rem 0.9rem; }
  .ok { color: #0a7; }
  .err { color: #c00; }
</style>
</head>
<body>
<h1>注册管理员</h1>
<p>此页只绑在本机 <code>127.0.0.1:{port}</code>，局域网打不开。账号建好后到
<code>http://127.0.0.1:{site}</code> 或家里其它设备的 <code>:{site}</code> <strong>登录</strong>。
做题页上的注册是普通用户，不会变成管理员。</p>
{body}
</body>
</html>
"""

_FORM = """
<form method="post" action="/register">
  <label>用户名</label>
  <input name="username" required minlength="3" maxlength="32" pattern="[A-Za-z0-9_]+" autocomplete="username"/>
  <label>密码</label>
  <input name="password" type="password" required minlength="4" maxlength="72" autocomplete="new-password"/>
  <button type="submit">注册为管理员</button>
</form>
{msg}
"""


def _form(msg: str = "") -> str:
    return _FORM.replace("{msg}", msg)


def _html(body: str) -> HTMLResponse:
    html = (
        _PAGE.replace("{port}", str(ADMIN_REGISTER_PORT))
        .replace("{site}", str(PORT))
        .replace("{body}", body)
    )
    return HTMLResponse(html)


def _is_loopback(request: Request) -> bool:
    host = (request.client.host if request.client else "") or ""
    host = host.strip("[]").lower()
    if host in {"127.0.0.1", "::1", "localhost"}:
        return True
    if host.startswith("::ffff:"):
        return host[7:] == "127.0.0.1"
    return False


@app.middleware("http")
async def refuse_non_loopback(request: Request, call_next):
    if not _is_loopback(request):
        return JSONResponse({"detail": "只允许评测机本机注册管理员"}, status_code=403)
    return await call_next(request)


@app.exception_handler(HTTPException)
async def http_to_form(request: Request, exc: HTTPException):
    if "json" in (request.headers.get("content-type") or "").lower():
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return _html(_form(f'<p class="err">{exc.detail}</p>'))


@app.get("/", response_class=HTMLResponse)
def form() -> HTMLResponse:
    return _html(_form())


async def _parse_register(request: Request) -> RegisterIn:
    ctype = (request.headers.get("content-type") or "").lower()
    try:
        if "json" in ctype:
            return RegisterIn.model_validate(await request.json())
        form = await request.form()
        return RegisterIn(
            username=str(form.get("username") or ""),
            password=str(form.get("password") or ""),
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


@app.post("/register")
async def register(request: Request, db: Session = Depends(get_db)):
    body = await _parse_register(request)
    user = create_user(db, body.username, body.password, is_admin=True)
    ctype = (request.headers.get("content-type") or "").lower()
    if "json" in ctype:
        return UserOut(id=user.id, username=user.username, is_admin=user.is_admin)
    return _html(
        f'<p class="ok">管理员 <strong>{user.username}</strong> 已创建。'
        f"请到 :{PORT} 登录，不要在本页登录。</p>"
        + _form()
    )
