from urllib.parse import urlencode, urljoin
import json
import os

import httpx

TOKEN_URL = 'https://discord.com/api/v8/oauth2/token'
BASE_DISCORD_API_URL = 'https://discord.com/api/v8/'
AUTHORIZE_URL = 'https://discord.com/oauth2/authorize'


class Oauth:
    def __init__(self, client_id: str, client_secret: str, scope: [str], redirect_uri: str):
        self.client_secret = client_secret
        self.client_id = client_id

        self.scope = scope
        self.redirect_uri = redirect_uri

    def authorization_url(self, **kwargs):
        args = {
            "client_id": self.client_id,
            "redirect_uri": urljoin(os.getenv("DASH_HOST_URL", "https://mybot-discord.com/"), self.redirect_uri),
            "response_type": "code",
            "scope": " ".join(self.scope)
        }
        args.update(kwargs)
        return AUTHORIZE_URL + "?" + urlencode(args, True)

    async def fetch_token(self, code):
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': "authorization_code",
            'code': code,
            'redirect_uri': urljoin(os.getenv("DASH_HOST_URL", "https://mybot-discord.com/"), self.redirect_uri),
            'scope': ' '.join(self.scope)
        }

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url=TOKEN_URL, data=data) as response:
                token = await response.read()

        try: return json.loads(token)
        except: return

    async def get(self, endpoint, token=None):
        url = BASE_DISCORD_API_URL + endpoint

        headers = {}
        if token:
            headers.update({"Authorization": f"Bearer {token}"})

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url=url) as response:
                datas = await response.read()

        return json.loads(datas)
