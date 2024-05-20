#!/usr/bin/env python3
import argparse
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, TypedDict

from fastapi import FastAPI
from sqlalchemy.ext.asyncio.engine import AsyncEngine, create_async_engine
import uvicorn

import config
from models import reset_accounts


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
    args = parser.parse_args()

    if args.reset_accounts:
        Config.reset_accounts = True

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
