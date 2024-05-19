#!/usr/bin/env python3
import argparse
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, TypedDict

import uvicorn
from fastapi import FastAPI
from sqlalchemy import Engine

import config
from models import create_db, get_engine, reset_accounts


@dataclass
class Config:
    create_tables: bool = False
    reset_accounts: bool = False


class LifespanState(TypedDict):
    db_engine: Engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[LifespanState]:
    """Configure app lifespan."""
    settings: config.Settings = config.get_settings()
    engine: Engine = get_engine(settings.database_url)
    if Config.create_tables:
        create_db(engine)
    if Config.reset_accounts:
        reset_accounts(engine, settings.number_of_fake_accounts)
    lifespan_state: LifespanState = {
        "db_engine": engine,
    }
    yield lifespan_state
    engine.dispose()


app: FastAPI = FastAPI(lifespan=lifespan)


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
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

    if args.create_tables:
        Config.create_tables = True

    if args.reset_accounts:
        Config.reset_accounts = True

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
