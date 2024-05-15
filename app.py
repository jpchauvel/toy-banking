#!/usr/bin/env python3
import os
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, TypedDict
import argparse
import fastenv
from fastapi import FastAPI, Request
import uvicorn


@dataclass
class Config:
    enable_fastenv: bool = False


class LifespanState(TypedDict):
    settings: fastenv.DotEnv


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[LifespanState]:
    """Configure app lifespan."""
    if Config.enable_fastenv:
        settings = await fastenv.load_dotenv(".env")
    else:
        settings = fastenv.DotEnv(**os.environ)
    lifespan_state: LifespanState = {"settings": settings}
    yield lifespan_state


app = FastAPI(lifespan=lifespan)


@app.get("/settings")
async def get_settings(request: Request) -> dict[str, str]:
    settings = request.state.settings
    return dict(settings)


def main():
    parser = argparse.ArgumentParser()
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
    args = parser.parse_args()

    if args.enable_fastenv:
        Config.enable_fastenv = True

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
