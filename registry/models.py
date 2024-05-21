from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, computed_field
from sqlalchemy import Column, JSON, MetaData, String, ScalarResult
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

import config

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata: MetaData = SQLModel.metadata
metadata.naming_convention = NAMING_CONVENTION


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


async def reset_banks(engine: AsyncEngine) -> None:
    async with AsyncSession(engine) as session:
        bank_statement = select(Bank)
        bank_results_exec: ScalarResult[Bank] = await session.exec(
            bank_statement
        )
        bank_results = bank_results_exec.all()
        [session.delete(row) for row in bank_results]
        await session.commit()


async def register_bank(engine: AsyncEngine, dto: BankDTO) -> None:
    async with AsyncSession(engine) as session:
        bank_statement = select(Bank).where(Bank.swift == dto.swift)
        bank_results = await session.exec(bank_statement)
        bank_results = bank_results.all()
        if len(bank_results) > 0:
            raise SwiftAlreadyExistException(
                f"Swift code {dto.swift} already exists"
            )
        bank: Bank = Bank(**dto.model_dump())
        session.add(bank)
        await session.commit()


async def update_bank(engine: AsyncEngine, dto: BankDTO) -> None:
    async with AsyncSession(engine) as session:
        bank_statement = select(Bank).where(Bank.swift == dto.swift)
        bank_exec: ScalarResult[Bank] = await session.exec(bank_statement)
        bank = bank_exec.one()
        bank.name = dto.name
        bank.bank_metadata = dto.bank_metadata
        session.add(bank)
        await session.commit()


async def retrieve_all_banks(engine: AsyncEngine) -> list[BankDTO]:
    async with AsyncSession(engine) as session:
        bank_statement = select(Bank)
        bank_results_exec: ScalarResult[Bank] = await session.exec(
            bank_statement
        )
        bank_results = bank_results_exec.all()
        return [BankDTO(**bank.model_dump()) for bank in bank_results]


async def retrieve_bank_by_swift(
    engine: AsyncEngine, swift: str
) -> BankDTO | None:
    async with AsyncSession(engine) as session:
        bank_statement = select(Bank).where(Bank.swift == swift)
        bank_exec: ScalarResult[Bank] = await session.exec(bank_statement)
        bank: Bank | None = bank_exec.first()
        if bank is None:
            return None
        return BankDTO(**bank.model_dump())
