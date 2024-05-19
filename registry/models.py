#!/usr/bin/env python3
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, computed_field
from sqlalchemy import Column, Engine, JSON, String
from sqlmodel import Field, SQLModel, Session, create_engine, select

import config


class BankException(Exception):
    pass


class SwiftAlreadyExistException(BankException):
    pass


class Bank(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True
    )
    swift: str = Field(sa_column=Column("swift", String, unique=True))
    name: str
    bank_metadata: str = Field(sa_column=Column("bank_metadata", JSON))


class BankDTO(BaseModel):
    swift: str
    name: str
    bank_metadata: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def link(self) -> str:
        settings: config.Settings = config.get_settings()
        return f"{settings.base_url}/banks/{self.swift}"


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
            raise SwiftAlreadyExistException(
                f"Swift code {dto.swift} already exists"
            )
        bank: Bank = Bank(**dto.model_dump())
        session.add(bank)
        session.commit()


def update_bank(engine: Engine, dto: BankDTO) -> None:
    with Session(engine) as session:
        bank_statement = select(Bank).where(Bank.swift == dto.swift)
        bank: Bank = session.exec(bank_statement).one()
        bank.name = dto.name
        bank.bank_metadata = dto.bank_metadata
        session.add(bank)
        session.commit()


def retrieve_all_banks(engine: Engine) -> list[Bank]:
    with Session(engine) as session:
        bank_statement = select(Bank)
        bank_results = session.exec(bank_statement).all()
        return bank_results


def retrieve_bank_by_swift(engine: Engine, swift: str) -> Bank | None:
    with Session(engine) as session:
        bank_statement = select(Bank).where(Bank.swift == swift)
        bank_results: Bank | None = session.exec(bank_statement).first()
        return bank_results
