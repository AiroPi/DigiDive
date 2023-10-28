from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import httpx


try:
    from dotenv import load_dotenv
except ImportError:
    pass
else:
    load_dotenv()

OAUTH_CLIENT_ID = os.environ["OAUTH_CLIENT_ID"]
OAUTH_CLIENT_SECRET = os.environ["OAUTH_CLIENT_SECRET"]
NOTION_AUTH_URL = os.environ["NOTION_AUTH_URL"]
NOTION_OAUTH_TOKEN = "https://api.notion.com/v1/oauth/token"


app = FastAPI()
app.mount("/static", StaticFiles(directory="src/static"), name="static")
templates = Jinja2Templates(directory="src/templates")

@app.api_route("/dive/{code}", methods=["GET"], response_class=HTMLResponse)
def dive_redirect(request: Request, code: str):
    return templates.TemplateResponse("login.html.j2", {"request": request, "redirect_uri": NOTION_AUTH_URL})


@app.get("/callback")
async def callback(request: Request, state: str, error: str | None = None, code: str | None = None):
    if error is not None:
        return error
    if code is not None:
        async with httpx.AsyncClient() as client:
            response = await client.post(NOTION_OAUTH_TOKEN, data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "http://localhost:8000/callback",
            }, auth=(OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET))
        print(response.json())
        return code
    
