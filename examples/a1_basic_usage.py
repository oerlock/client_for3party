"""
Demonstrate the basic usage of a real third-party API([Resolve Pay API](https://resolvepay.redoc.ly/2021-05-01#operation/listCustomers)):

Use the API to generate an invoice.
"""
import asyncio
import logging

import aiohttp
from aiohttp import BasicAuth
from pydantic import HttpUrl, EmailStr, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.client_for3party.client import ClientBase

logger = logging.getLogger(__name__)


class ClientResolvePay(ClientBase):
    def __init__(self, base_url: HttpUrl, auth: BasicAuth, session: aiohttp.ClientSession | None = None):
        super(ClientResolvePay, self).__init__(base_url, session)
        self.auth = auth

    async def aget_users_by_email(self, email: EmailStr) -> list:
        url = f"{self.base_url}api/customers"
        params = {
            "page": "1",
            "filter[email][eq]": email,
            "filter[archived][eq]": 'false',
        }
        async with self.session.get(url, params=params, auth=self.auth) as resp:
            if not await self.is_success(resp):
                return []
            data = await resp.json()
        return data['results']


class HeaderBaseAuth(BaseModel):
    username: str
    password: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter='__')

    base_url: HttpUrl
    header_base_auth: HeaderBaseAuth
    test_account_resolve_pay: str


settings = Settings()


async def main():
    async with ClientResolvePay(settings.base_url, BasicAuth(settings.header_base_auth.username,
                                                             settings.header_base_auth.password)) as client:
        rs = await client.aget_users_by_email(settings.test_account_resolve_pay)
    return rs


if __name__ == '__main__':
    tmp_rs = asyncio.run(main())
    print(tmp_rs)
