#!/usr/bin/env python3
import argparse
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, AsyncIterator, TypedDict

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import Engine

import config
from models import (
    BankDTO,
    SwiftAlreadyExistException,
    create_db,
    get_engine,
    register_bank,
    reset_banks,
    retrieve_all_banks,
    retrieve_bank_by_swift,
    update_bank,
)


@dataclass
class Config:
    create_tables: bool = False
    reset_banks: bool = False


class LifespanState(TypedDict):
    db_engine: Engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[LifespanState]:
    """Configure app lifespan."""
    settings: config.Settings = config.get_settings()
    engine: Engine = get_engine(settings.database_url)
    if Config.create_tables:
        create_db(engine)
    if Config.reset_banks:
        reset_banks(engine)
    lifespan_state: LifespanState = {
        "db_engine": engine,
    }
    yield lifespan_state
    engine.dispose()


app: FastAPI = FastAPI(lifespan=lifespan)


@app.post("/banks/controllers/sync", status_code=status.HTTP_201_CREATED)
async def sync_bank_endpoint(
    request: Request,
    bank: BankDTO,
    settings: Annotated[config.Settings, Depends(config.get_settings)],
) -> Response:
    engine = request.state.db_engine
    bank_result = retrieve_bank_by_swift(engine, bank.swift)
    if bank_result is None:
        register_bank(engine, bank)
        return Response(
            status_code=status.HTTP_201_CREATED,
            content=None,
            headers={"Location": f"{settings.base_url}/banks/{bank.swift}"},
        )
    else:
        update_bank(engine, bank)
        return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/banks", status_code=status.HTTP_201_CREATED)
async def regiter_bank_endpoint(
    request: Request,
    bank: BankDTO,
    settings: Annotated[config.Settings, Depends(config.get_settings)],
) -> Response:
    engine = request.state.db_engine
    try:
        register_bank(engine, bank)
    except SwiftAlreadyExistException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        )
    return Response(
        status_code=status.HTTP_201_CREATED,
        content=None,
        headers={"Location": f"{settings.base_url}/banks/{bank.swift}"},
    )


@app.put("/banks/{swift}")
async def update_bank_endpoint(
    request: Request,
    swift: str,
    bank: BankDTO,
) -> Response:
    engine = request.state.db_engine
    bank_result = retrieve_bank_by_swift(engine, swift)
    if bank_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No bank service with swift code {swift} found",
        )
    if swift != bank.swift:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Swift in payload does not match resource",
        )
    update_bank(engine, bank)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/banks")
async def list_banks_endpoint(request: Request) -> list[BankDTO]:
    engine = request.state.db_engine
    bank_results = retrieve_all_banks(engine)
    return [BankDTO(**bank.model_dump()) for bank in bank_results]


@app.get("/banks/{swift}")
async def get_bank_by_swift_endpoint(request: Request, swift: str) -> BankDTO:
    engine = request.state.db_engine
    bank = retrieve_bank_by_swift(engine, swift)
    if bank is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No bank service with swift code {swift} found",
        )
    return BankDTO(**bank.model_dump())


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
        "--reset-banks",
        action="store_true",
        default=False,
        help="Reset bank services",
    )
    args = parser.parse_args()

    if args.create_tables:
        Config.create_tables = True

    if args.reset_banks:
        Config.reset_banks = True

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
