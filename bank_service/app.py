#!/usr/bin/env python3
import argparse
import asyncio
import random
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, TypedDict

import aiohttp
import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from sqlalchemy.ext.asyncio.engine import AsyncEngine, create_async_engine

import config
from models import BankAccountDTO, reset_accounts, retrieve_all_bank_accounts


@dataclass
class Config:
    reset_accounts: bool = False


class LifespanState(TypedDict):
    db_engine: AsyncEngine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[LifespanState]:
    """Configure app lifespan."""
    settings: config.Settings = config.get_settings()
    engine: AsyncEngine = create_async_engine(settings.database_url, echo=True)
    if Config.reset_accounts:
        await reset_accounts(engine, settings.number_of_fake_accounts)
    lifespan_state: LifespanState = {
        "db_engine": engine,
    }
    yield lifespan_state
    await engine.dispose()


app: FastAPI = FastAPI(lifespan=lifespan)


@app.get("/accounts")
async def list_accounts_endpoint(request: Request) -> list[BankAccountDTO]:
    engine = request.state.db_engine
    account_results: list[BankAccountDTO] = await retrieve_all_bank_accounts(
        engine
    )
    return account_results


@app.get("/accounts/functions/random")
async def list_random_accounts_endpoint(
    request: Request, n: int = 1
) -> list[BankAccountDTO]:
    engine = request.state.db_engine
    account_results: list[BankAccountDTO] = await retrieve_all_bank_accounts(
        engine
    )
    if len(account_results) < n:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Not enough bank accounts found",
        )
    random_accounts: list[BankAccountDTO] = random.sample(account_results, n)
    return random_accounts


async def process_registration() -> None:
    settings: config.Settings = config.get_settings()
    payload: dict[str, Any] = {
        "swift": settings.swift,
        "name": settings.bank_name,
        "bank_metadata": {
            "region": settings.bank_region,
            "country": settings.bank_country,
            "toy_network_queue_name": settings.toy_network_queue_name,
        },
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                settings.registration_url,
                json=payload,
                timeout=settings.registration_timeout,
            ) as response:
                if response.status not in (201, 204):
                    raise Exception("Failed to register bank")
        except aiohttp.ServerTimeoutError as err:
            raise Exception("Failed to register bank. Timeout.") from err
        except aiohttp.ClientConnectionError as err:
            raise Exception(
                "Failed to register bank. Connection error."
            ) from err


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Hostname"
    )
    parser.add_argument("--port", type=int, default=8000, help="Port")
    parser.add_argument(
        "--reset-accounts",
        action="store_true",
        default=False,
        help="Reset accounts",
    )
    parser.add_argument(
        "--register-service",
        action="store_true",
        default=False,
        help="Register Service",
    )
    args = parser.parse_args()

    if args.reset_accounts:
        Config.reset_accounts = True

    if args.register_service:
        asyncio.run(process_registration())

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
