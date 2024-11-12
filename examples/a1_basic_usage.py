"""
Demonstrate the basic usage of a real third-party API([Resolve Pay API](https://resolvepay.redoc.ly/2021-05-01#operation/createInvoice)):

Use the API to generate an invoice.
"""
import asyncio
import logging
import time
from enum import Enum

import aiohttp
from aiohttp import BasicAuth
from pydantic import HttpUrl, EmailStr, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.client_for3party.client import ClientBase

logger = logging.getLogger(__name__)


class Terms(str, Enum):
    # TODO: add more type about terms
    net30 = 'net30'


class AdvanceReqeust(str, Enum):
    T = 'true'
    F = 'false'


class PayloadInvoiceBase(BaseModel):
    terms: Terms | None = Terms.net30
    merchant_invoice_url: str | None = None
    number: str | None = None
    order_number: str | None = None
    po_number: str | None = None
    notes: str | None = None
    customer_id: str | None = None
    advance_requested: AdvanceReqeust | None = AdvanceReqeust.T
    # TODO: Use the Decimal type and automatically convert it to float when converting to JSON.
    amount: float | None = None


class PayloadInvoiceCreate(PayloadInvoiceBase):
    merchant_invoice_url: str
    number: str
    customer_id: str
    amount: float


class PayloadUpdateInvoiceCreate(PayloadInvoiceBase):
    pass


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

    async def aget_user_by_email(self, email: EmailStr) -> dict:
        infos_user = await self.aget_users_by_email(email)
        if len(infos_user) > 1:
            logger.warning(f'[ClientResolvePay][aget_user_by_email]: There is more than one user with email: {email}')
        return infos_user[0] if infos_user else {}

    async def aget_user_by_id(self, customer_id: str) -> dict:
        url = f"{self.base_url}api/customers/{customer_id}"
        async with self.session.get(url, auth=self.auth) as resp:
            if not await self.is_success(resp):
                return {}
            return await resp.json()

    async def acreate_an_invoice(self, info_payload: PayloadInvoiceCreate):
        url = f"{self.base_url}api/invoices"
        payload = info_payload.model_dump(exclude_none=True)
        async with self.session.post(url, auth=self.auth, json=payload) as resp:
            if not await self.is_success(resp):
                return {}
            return await resp.json()

    async def aupdate_invoice(self, invoice_id: str, info_payload: PayloadUpdateInvoiceCreate):
        url = f"{self.base_url}api/invoices/{invoice_id}"
        payload = info_payload.model_dump(exclude_unset=True)
        async with self.session.put(url, auth=self.auth, json=payload) as resp:
            if not await self.is_success(resp):
                return {}
            return await resp.json()

    async def asend_invoice(self, invoice_id: str):
        url = f"{self.base_url}api/invoices/{invoice_id}/send"
        async with self.session.put(url, auth=self.auth) as resp:
            if not await self.is_success(resp):
                return {}
            return await resp.json()


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
        rs = await client.aget_user_by_email(settings.test_account_resolve_pay)
        assert rs
        info_payload = PayloadInvoiceCreate(merchant_invoice_url='https://example.com/invoice.pdf',
                                            number=f'ER{int(time.time())}',
                                            customer_id=rs['id'], amount='100.00')
        rs = await client.acreate_an_invoice(info_payload)
        assert rs
        info_payload = PayloadUpdateInvoiceCreate(amount='90.01')
        rs = await client.aupdate_invoice(rs['id'], info_payload)
        assert rs
        rs = await client.asend_invoice(rs['id'])
        assert rs


if __name__ == '__main__':
    asyncio.run(main())
