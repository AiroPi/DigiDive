from __future__ import annotations

import os
import re
from typing import Annotated, Any, Literal
from urllib.parse import urlencode, urljoin

import httpx
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware import Middleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastui import AnyComponent, FastUI, components as c, prebuilt_html
from fastui.components.display import DisplayLookup
from fastui.events import GoToEvent, PageEvent
from fastui.forms import SelectOption
from pydantic import BaseModel, computed_field
from sqlalchemy import delete, select
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
NOTION_OAUTH_TOKEN = "https://api.notion.com/v1/oauth/token"  # noqa: S105
BASE_URL = os.environ["BASE_URL"]


app = FastAPI(middleware=[Middleware(SessionMiddleware, secret_key=os.environ["SECRET"])])
app.mount("/static", StaticFiles(directory="./static"), name="static")
templates = Jinja2Templates(directory="./templates")

database = create_async_engine("sqlite+aiosqlite:///data/save.db")
async_session = async_sessionmaker(database, expire_on_commit=False)


class Dive(BaseModel):
    link: str
    number: str
    name: str
    linked: bool = False

    # @computed_field
    # @property
    # def unlink_url(self) -> c.Image:
    #     return c.Image(
    #         src="https://www.nicepng.com/png/detail/208-2086588_trash-can-icon.png",
    #         on_click=GoToEvent(url="/delete", query={"link": self.link}),
    #     )
    @computed_field
    @property
    def unlink_url(self) -> str:
        return f"/delete?link={self.link}"

    @computed_field
    @property
    def unlink(self) -> str:
        return "unlink" if self.linked else "-"


def format_auth_url(redirect_uri: str, state: str | None = None) -> str:
    params = {
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
    }
    if state is not None:
        params["state"] = state
    return f"{NOTION_AUTH_URL}?{urlencode(params)}"


def get_number(request: Request, dive: dict[str, Any]) -> str | int:
    prop = dive["properties"][request.session["column"]]
    if prop["type"] == "number":
        return prop["number"]
    return dive["properties"]["_number"]["formula"]["string"]


def get_fixed_url(url: str) -> str:
    """
    The Notion API returns publics url as "https://user.notion.site/name-of-the-page-{id}". But only the id is needed.
    If the name of the page change, the returned url will also change, which is not ideal for us to detect linked pages.
    This function will return the fixed url, which is the url without the name of the page.

    For example: "https://airopi.notion.site/Plong-e-pr-pa-GP-4-abd78zZoiu7878oiuy7878" -> "https://airopi.notion.site/abd78zZoiu7878oiuy7878
    """
    return re.sub(r"^(https://\S+\.notion\.site/)\S*?([^-]+)$", r"\1\2", url)


def page(*components: AnyComponent, title: str | None = None) -> list[AnyComponent]:
    return [
        c.PageTitle(text="DigiDive"),
        c.Navbar(
            title="DigiDive v0.5",
            title_event=GoToEvent(url="/"),
            start_links=[
                c.Link(
                    components=[c.Text(text="Config")],
                    on_click=GoToEvent(url="/config"),
                    active="startswith:/config",
                ),
                c.Link(
                    components=[c.Text(text="Logout")],
                    on_click=GoToEvent(url="/logout"),
                ),
            ],
        ),
        c.Page(
            components=[
                *((c.Heading(text=title),) if title else ()),
                *components,
            ],
        ),
        c.Footer(
            extra_text="DigiDive",
            links=[
                c.Link(
                    components=[c.Text(text="Github")], on_click=GoToEvent(url="https://github.com/AiroPi/DigiDive")
                ),
            ],
        ),
    ]


@app.get("/api/", response_model=FastUI, response_model_exclude_none=True)
async def index(request: Request) -> list[AnyComponent]:
    if request.session.get("access_token") is None:
        return page(
            c.Button(text="Login with Notion", on_click=GoToEvent(url=format_auth_url(urljoin(BASE_URL, "/callback"))))
        )

    if request.session.get("database") is None:
        return [c.FireEvent(event=GoToEvent(url="/config/table"))]
    if request.session.get("column") is None:
        return [c.FireEvent(event=GoToEvent(url="/config/column"))]

    notion_client = NotionClient(request.session["access_token"])

    async with notion_client:
        dives_log = await notion_client.query_database(
            request.session["database"],
            sorts=[{"property": request.session["column"], "direction": "descending"}],
        )

    dives = [
        Dive(
            link=dive["public_url"],
            name=title[0]["plain_text"] if (title := dive["properties"]["Name"]["title"]) else "Untitled",
            number=str(get_number(request, dive)),
        )
        for dive in dives_log.json()["results"]
    ]
    async with async_session() as session:
        expr = (
            select(Bind.link)
            .filter_by(user_id=request.session["owner"]["user"]["id"])
            .filter(Bind.link.in_(get_fixed_url(dive.link) for dive in dives))
        )
        result = await session.execute(expr)
        existing = {link for (link,) in result}
    for dive in dives:
        dive.linked = get_fixed_url(dive.link) in existing

    return page(
        c.Table(
            data=dives,
            columns=[
                DisplayLookup(field="name", title="Name", on_click=GoToEvent(url="{link}")),
                DisplayLookup(field="number", title="Number"),
                DisplayLookup(field="linked", title="Linked"),
                DisplayLookup(field="unlink", title="Unlink", on_click=GoToEvent(url="{unlink_url}")),
            ],
        )
    )


@app.get("/api/dive/{code}", response_model=FastUI, response_model_exclude_none=True)
async def dive_redirect(request: Request, code: str) -> list[AnyComponent]:
    async with async_session() as session:
        result = await session.scalar(select(Bind).filter_by(code=code))
    if result is not None:
        return [c.FireEvent(event=GoToEvent(url=result.link))]

    if request.session.get("access_token") is None:
        return page(
            c.Button(
                text="Login with Notion", on_click=GoToEvent(url=format_auth_url(urljoin(BASE_URL, "/callback"), code))
            )
        )
    # TODO: save state during config?
    if request.session.get("database") is None:
        return [c.FireEvent(event=GoToEvent(url="/config/table"))]
    if request.session.get("column") is None:
        return [c.FireEvent(event=GoToEvent(url="/config/column"))]

    notion_client = NotionClient(request.session["access_token"])
    async with notion_client:
        dives_raw = await notion_client.query_database(
            request.session["database"],
            sorts=[{"timestamp": "last_edited_time", "direction": "descending"}],
        )
        dives = [
            Dive(
                link=get_fixed_url(dive["public_url"]),
                name=title[0]["plain_text"] if (title := dive["properties"]["Name"]["title"]) else "Untitled",
                number=str(get_number(request, dive)),
            )
            for dive in dives_raw.json()["results"]
        ]
        async with async_session() as session:
            expr = (
                select(Bind.link)
                .filter_by(user_id=request.session["owner"]["user"]["id"])
                .filter(Bind.link.in_(dive.link for dive in dives))
            )
            result = await session.execute(expr)
            existing = {link for (link,) in result}
        for dive in dives:
            dive.linked = dive.link in existing

        options = [
            SelectOption(value=dive.link, label=f"{dive.number} - {dive.name}") for dive in dives if not dive.linked
        ]
        tables_select_field = c.forms.FormFieldSelect(
            options=options,
            title="Select Dive",
            name="dive_url",
            multiple=False,
        )
        return page(
            c.Paragraph(text="Select the dive to bind."),
            c.Form(form_fields=[tables_select_field], submit_url=f"/api/dive/{code}"),
        )


@app.post("/api/dive/{code}", response_model=FastUI, response_model_exclude_none=True)
async def dive_post(request: Request, dive_url: Annotated[str, Form()], code: str):
    async with async_session() as session:
        result = Bind(link=dive_url, user_id=request.session["owner"]["user"]["id"], code=code)
        session.add(result)
        await session.commit()
    return [c.FireEvent(event=GoToEvent(url=dive_url))]


type ConfigKind = Literal["table", "column"]


@app.get("/api/config/{kind}", response_model=FastUI, response_model_exclude_none=True)
async def forms_view(request: Request, kind: ConfigKind) -> list[AnyComponent]:
    return page(
        c.LinkList(
            links=[
                c.Link(
                    components=[c.Text(text="Config table")],
                    on_click=PageEvent(name="change-form", push_path="/config/table", context={"kind": "table"}),
                    active="/config/table",
                ),
                c.Link(
                    components=[c.Text(text="Config column")],
                    on_click=PageEvent(name="change-form", push_path="/config/column", context={"kind": "column"}),
                    active="/config/column",
                ),
            ],
            mode="tabs",
            class_name="+ mb-4",
        ),
        c.ServerLoad(
            path="/config/content/{kind}",
            load_trigger=PageEvent(name="change-form"),
            components=await form_content(request, kind),
        ),
        title="Forms",
    )


@app.get("/api/config/content/{kind}", response_model=FastUI, response_model_exclude_none=True)
async def form_content(request: Request, kind: ConfigKind) -> list[AnyComponent]:
    if request.session.get("access_token") is None:
        return [c.FireEvent(event=GoToEvent(url="/"))]
    match kind:
        case "table":
            notion_client = NotionClient(request.session["access_token"])
            async with notion_client:
                result = await notion_client.search("", filter={"value": "database", "property": "object"})
                tables = result.json()["results"]
                tables_options = [
                    SelectOption(value=table["id"], label=table["title"][0]["plain_text"]) for table in tables
                ]
                tables_select_field = c.forms.FormFieldSelect(
                    options=tables_options,
                    title="Select Table",
                    name="value",
                    multiple=False,
                    initial=request.session.get("database"),
                )
                return [
                    c.Paragraph(text="Select the table with your dives."),
                    c.Form(form_fields=[tables_select_field], submit_url="/api/config/table"),
                ]
        case "column":
            if request.session.get("database") is None:
                return [c.Markdown(text="Please select a table first.")]

            notion_client = NotionClient(request.session["access_token"])
            async with notion_client:
                if (table := request.session.get("database")) is None:
                    return [c.FireEvent(event=GoToEvent(url="/config/table"))]
                result = await notion_client.retrieve_database(table)
                properties = result.json()["properties"]
                options = [
                    SelectOption(value=prop["name"], label=prop["name"])
                    for prop in properties.values()
                    if prop["type"] in ["number", "formula"]
                ]
                field = c.forms.FormFieldSelect(
                    options=options,
                    title="Select Column",
                    name="value",
                    multiple=False,
                    initial=request.session.get("column"),
                )
            return [
                c.Paragraph(text="Select the column corresponding to the dive number."),
                c.Form(form_fields=[field], submit_url="/api/config/column"),
            ]


@app.get("/api/config", response_model=FastUI, response_model_exclude_none=True)
async def config_get() -> list[AnyComponent]:
    return [c.FireEvent(event=GoToEvent(url="/config/table"))]


@app.post("/api/config/{kind}", response_model=FastUI, response_model_exclude_none=True)
async def config_post(request: Request, kind: ConfigKind, value: Annotated[str, Form()]):
    match kind:
        case "table":
            request.session["database"] = value
            return [c.FireEvent(event=GoToEvent(url="/config/column"))]
        case "column":
            request.session["column"] = value
            return [c.FireEvent(event=GoToEvent(url="/"))]


@app.get("/api/delete", response_model=FastUI, response_model_exclude_none=True)
async def delete_dive(request: Request, link: str):
    if request.session.get("access_token") is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    async with async_session() as session:
        result = await session.execute(select(Bind).filter_by(link=get_fixed_url(link)))
        bind = result.scalar_one_or_none()
        if bind is None:
            raise HTTPException(status_code=404, detail="Not Found")
        if bind.user_id != request.session["owner"]["user"]["id"]:
            raise HTTPException(status_code=403, detail="Forbidden")
        await session.delete(bind)
        await session.commit()
    return [c.FireEvent(event=GoToEvent(url="/"))]


@app.get("/login/{code}", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
async def login(request: Request, code: str | None = None):
    return templates.TemplateResponse(
        "login.html.j2",
        {
            "request": request,
            "redirect_uri": format_auth_url(urljoin(BASE_URL, "/callback"), code),
        },
    )


@app.get("/api/logout", response_model=FastUI, response_model_exclude_none=True)
async def logout(request: Request) -> list[AnyComponent]:
    request.session.clear()
    return [c.FireEvent(event=GoToEvent(url="/"))]


@app.get("/callback", response_class=RedirectResponse)
async def callback(request: Request, state: str, error: str | None = None, code: str | None = None):
    if error is not None:
        return error
    if code is not None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                NOTION_OAUTH_TOKEN,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": urljoin(BASE_URL, "/callback"),
                },
                auth=(OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET),
            )
        request.session.update(response.json())
        return RedirectResponse(url=f"/dive/{state}" if state else "/")


@app.get("/{path:path}")
async def html_landing() -> HTMLResponse:
    """Simple HTML page which serves the React app, comes last as it matches all paths."""
    return HTMLResponse(prebuilt_html(title="FastUI Demo"))
