#!/usr/bin/env python3
import uuid
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Column, Engine, String, JSON
from sqlmodel import Field, SQLModel, Session, create_engine, select


class BankException(Exception):
    pass


class SwiftAlreadyExistException(BankException):
    pass


class Bank(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True
    )
    swift: str = Field(
        sa_column=Column("swift", String, unique=True)
    )
    name: str
    bank_metadata: str = Field(
        sa_column=Column("bank_metadata", JSON)
    )


class BankDTO(BaseModel):
    swift: str
    name: str
    bank_metadata: dict[str, Any]


def get_engine(database_url: str) -> Engine:
    engine: Engine = create_engine(database_url)
    SQLModel.metadata.create_all(engine)
    return engine


def create_db(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)


def reset_banks(engine: Engine) -> None:
    with Session(engine) as session:
        bank_statement = select(Bank)
        bank_results = session.exec(bank_statement).all()
        [session.delete(row) for row in bank_results]
        session.commit()


def register_bank(engine: Engine, dto: BankDTO) -> None:
    with Session(engine) as session:
        bank_statement = select(Bank).where(Bank.swift == dto.swift)
        bank_results = session.exec(bank_statement).all()
        if len(bank_results) > 0:
            raise SwiftAlreadyExistException(f"Swift code {dto.swift} already exists")
        bank: Bank = Bank(**dto.model_dump())
        session.add(bank)
        session.commit()
