#!/usr/bin/env python3
import argparse
from contextlib import asynccontextmanager
from dataclasses import dataclass
import os
from typing import Any, AsyncIterator, Optional, TypedDict

from fastapi import FastAPI, Request
import fastenv
from sqlalchemy import Engine
import uvicorn

from models import create_db, get_engine, reset_accounts


@dataclass
class Config:
    enable_fastenv: bool = False
    create_tables: bool = False
    reset_accounts: bool = False


class LifespanState(TypedDict):
    db_engine: Engine
    settings: fastenv.DotEnv


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[LifespanState]:
    """Configure app lifespan."""
    if Config.enable_fastenv:
        settings: fastenv.DotEnv = await fastenv.load_dotenv(".env")
    else:
        settings: fastenv.DotEnv = fastenv.DotEnv(**os.environ)
    database_url: str = settings.get("DATABASE_URL", "")
    engine: Engine = get_engine(database_url)
    if Config.create_tables:
        create_db(engine)
    if Config.reset_accounts:
        num_of_fake_accounts: int = int(
            settings.get("NUMBER_OF_FAKE_ACCOUNTS", 10)
        )
        reset_accounts(engine, num_of_fake_accounts)
    lifespan_state: LifespanState | None = {
        "db_engine": engine,
        "settings": settings,
    }
    for key, value in lifespan_state.items():
        setattr(app.state, key, value)
    yield lifespan_state
    for key, value in lifespan_state.items():
        tmp = getattr(app.state, key)
        del tmp
    engine.dispose()


app: FastAPI = FastAPI(lifespan=lifespan)


# FIXME: Remove this endpoint
@app.get("/settings")
async def get_settings(request: Request) -> dict[str, str]:
    settings = request.state.settings
    return dict(settings)


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument(
        "--enable-fastenv",
        action="store_true",
        default=False,
        help="Enable FastEnv (development mode)",
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Hostname"
    )
    parser.add_argument("--port", type=int, default=8000, help="Port")
    parser.add_argument(
        "--create-tables",
        action="store_true",
        default=False,
        help="Create tables",
    )
    parser.add_argument(
        "--reset-accounts",
        action="store_true",
        default=False,
        help="Reset accounts",
    )
    args = parser.parse_args()

    if args.enable_fastenv:
        Config.enable_fastenv = True

    if args.create_tables:
        Config.create_tables = True

    if args.reset_accounts:
        Config.reset_accounts = True

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
