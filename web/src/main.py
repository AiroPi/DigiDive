from __future__ import annotations

import os
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware import Middleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

try:
    from dotenv import load_dotenv
except ImportError:
    pass
else:
    load_dotenv()

OAUTH_CLIENT_ID = os.environ["OAUTH_CLIENT_ID"]
OAUTH_CLIENT_SECRET = os.environ["OAUTH_CLIENT_SECRET"]
NOTION_AUTH_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_OAUTH_TOKEN = "https://api.notion.com/v1/oauth/token"


app = FastAPI(
    middleware=[Middleware(SessionMiddleware, secret_key=os.environ["SECRET"])]
)
app.mount("/static", StaticFiles(directory="src/static"), name="static")
templates = Jinja2Templates(directory="src/templates")


def format_auth_url(redirect_uri: str, state: str) -> str:
    return f"{NOTION_AUTH_URL}?{urlencode({'client_id': OAUTH_CLIENT_ID, 'redirect_uri': redirect_uri, 'response_type': 'code', 'state': state})}"


@app.get("/")
async def index():
    return "Hello World"


@app.api_route("/dive/{code}", methods=["GET"], response_class=HTMLResponse)
def dive_redirect(request: Request, code: str):
    print(request.session)
    return templates.TemplateResponse(
        "login.html.j2",
        {
            "request": request,
            "redirect_uri": format_auth_url("http://localhost:8000/callback", code),
        },
    )


@app.get("/logout", response_class=RedirectResponse)
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


@app.get("/callback", response_class=RedirectResponse)
async def callback(
    request: Request, state: str, error: str | None = None, code: str | None = None
):
    if error is not None:
        return error
    if code is not None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                NOTION_OAUTH_TOKEN,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": "http://localhost:8000/callback",
                },
                auth=(OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET),
            )
        request.session.update(response.json())
        return RedirectResponse(url="/dive/{}".format(state))
