from __future__ import annotations

import os
from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.middleware import Middleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.middleware.sessions import SessionMiddleware

from core.database import Bind
from libraries.notion_api import NotionClient

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

database = create_async_engine("sqlite+aiosqlite:///data/save.db")
async_session = async_sessionmaker(database, expire_on_commit=False)


def format_auth_url(redirect_uri: str, state: str | None) -> str:
    params = {
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
    }
    if state is not None:
        params["state"] = state
    return f"{NOTION_AUTH_URL}?{urlencode(params)}"


# @app.on_event("startup")
# async def startup():
#     await

# @app.on_event("shutdown")
# async def shutdown():
#     pass


@app.get("/")
async def index(request: Request):
    return request.session


@app.api_route("/dive/{code}", methods=["GET"], response_class=HTMLResponse)
async def dive_redirect(request: Request, code: str):
    async with async_session() as session:
        result = await session.scalar(select(Bind).filter_by(code=code))
    if result is not None:
        return RedirectResponse(url=result.link)

    if request.session.get("access_token") is None:
        return RedirectResponse(url="/login/{}".format(code))
    elif request.session.get("database") is None:
        return RedirectResponse(url="/config")
    else:
        notion_client = NotionClient(request.session["access_token"])
        async with notion_client:
            dives_log = await notion_client.query_database(
                request.session["database"],
                sorts=[{"timestamp": "last_edited_time", "direction": "descending"}],
            )

        dives = [
            {
                "link": dive["public_url"],
                "number": dive["properties"]["_number"]["formula"]["string"],
            }
            for dive in dives_log.json()["results"]
        ]

        return templates.TemplateResponse(
            "select_dive.html.j2",
            {"request": request, "dives": dives},
        )


@app.post("/dive/{code}")
async def dive_post(request: Request, dive_url: Annotated[str, Form()], code: str):
    async with async_session() as session:
        bind = await session.scalar(select(Bind).filter_by(code=code))
        if bind is not None:
            pass
            # bind.link = dive_url
            # bind.user_id = request.session["owner"]["user"]["id"]
            # await session.commit()
        else:
            bind = Bind(
                code=code,
                user_id=request.session["owner"]["user"]["id"],
                link=dive_url,
            )
            session.add(bind)
            await session.commit()
    return RedirectResponse(url=dive_url, status_code=303)


@app.get("/config")
async def config_get(request: Request):
    print("get")
    if request.session.get("access_token") is None:
        return RedirectResponse(url="/login")
    notion_client = NotionClient(request.session["access_token"])
    async with notion_client:
        result = await notion_client.search(
            "", filter={"value": "database", "property": "object"}
        )
        return templates.TemplateResponse(
            "select_db.html.j2", {"request": request, "pages": result.json()["results"]}
        )


@app.post("/config")
async def config_post(request: Request, database: Annotated[str, Form()]):
    request.session["database"] = database
    return RedirectResponse(url="/", status_code=303)


@app.get("/login/{code}", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
async def login(request: Request, code: str | None = None):
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
        return RedirectResponse(url=f"/dive/{state}" if state else "/")
