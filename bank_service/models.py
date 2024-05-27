import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum, auto
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Column, MetaData, ScalarResult, String
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlmodel import JSON, Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from fake import generate_bank_account

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata: MetaData = SQLModel.metadata
metadata.naming_convention = NAMING_CONVENTION


class BankAccountStateType(StrEnum):
    ACTIVE = auto()
    CANCELED = auto()


class AccountTransactionStateType(StrEnum):
    PENDING = auto()
    COMPLETED = auto()
    CANCELED = auto()


class BankAccount(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True
    )
    name: str
    account_number: str = Field(
        sa_column=Column("account_number", String, unique=True)
    )
    state: str
    balance: Decimal

    async def calculate_balance(self, engine: AsyncEngine) -> Decimal:
        async with AsyncSession(engine) as session:
            account_transactions_exec: ScalarResult[AccountTransaction] = (
                await session.exec(
                    select(AccountTransaction).where(
                        AccountTransaction.account_id == self.id
                    )
                )
            )
            account_transactions = account_transactions_exec.all()
            balance: Decimal = Decimal(0)
            for account_transaction in account_transactions:
                if (
                    account_transaction.state
                    == AccountTransactionStateType.CANCELED
                ):
                    continue
                balance += account_transaction.amount
            return balance


class AccountTransaction(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True
    )
    account_id: uuid.UUID = Field(foreign_key="bankaccount.id")
    amount: Decimal = Field(default=0, max_digits=9, decimal_places=2)
    state: str
    annotations: str = Field(sa_column=Column("annotations", JSON, default=[]))
    description: str
    timestamp: datetime


class BankAccountDTO(BaseModel):
    id: uuid.UUID
    name: str
    account_number: str
    state: str
    balance: float


async def retrieve_all_bank_accounts(
    engine: AsyncEngine,
) -> list[BankAccountDTO]:
    async with AsyncSession(engine) as session:
        bank_account_statement = select(BankAccount)
        bank_account_results_exec: ScalarResult[BankAccount] = (
            await session.exec(bank_account_statement)
        )
        bank_account_results = bank_account_results_exec.all()
        return [
            BankAccountDTO(**account.model_dump())
            for account in bank_account_results
        ]


async def reset_accounts(engine: AsyncEngine, num_fake_accounts: int) -> None:
    """Generate bank accounts."""
    async with AsyncSession(engine) as session:
        bank_account_statement = select(BankAccount)
        bank_account_results_exec: ScalarResult[BankAccount] = (
            await session.exec(bank_account_statement)
        )
        bank_account_results = bank_account_results_exec.all()
        account_transaction_statement = select(AccountTransaction)
        account_transaction_results_exec: ScalarResult[AccountTransaction] = (
            await session.exec(account_transaction_statement)
        )
        account_transaction_results = account_transaction_results_exec.all()
        [session.delete(row) for row in bank_account_results]
        [session.delete(row) for row in account_transaction_results]
        await session.commit()

    for _ in range(num_fake_accounts):
        account_data: dict[str, str | Decimal] = generate_bank_account()
        balance: Decimal = account_data["balance"]
        account: BankAccount = BankAccount(**account_data)
        account_transaction: AccountTransaction = AccountTransaction(
            account_id=account.id,
            amount=balance,
            state=AccountTransactionStateType.COMPLETED,
            annotations=[],
            description="Initial deposit",
            timestamp=datetime.now(),
        )
        async with AsyncSession(engine) as session:
            session.add(account)
            session.add(account_transaction)
            await session.commit()


async def create_or_update_transaction(
    engine: AsyncEngine,
    transaction_id: uuid.UUID,
    account_number: str,
    state: AccountTransactionStateType,
    description: str,
    annotations: list[dict[str, Any]],
    amount: Decimal,
) -> None:
    async with AsyncSession(engine) as session:
        bank_account_statement = select(BankAccount)
        bank_account_statement = bank_account_statement.where(
            BankAccount.account_number == account_number
        )
        bank_account_results_exec: ScalarResult[BankAccount] = (
            await session.exec(bank_account_statement)
        )
        bank_account = bank_account_results_exec.one()

        account_transaction_statement = select(AccountTransaction)
        account_transaction_statement = account_transaction_statement.where(
            AccountTransaction.account_id == bank_account.id,
            AccountTransaction.id == transaction_id,
        )
        account_transaction_results_exec: ScalarResult[AccountTransaction] = (
            await session.exec(account_transaction_statement)
        )
        account_transaction = account_transaction_results_exec.first()
        if account_transaction is not None:
            account_transaction.amount = amount
            account_transaction.state = state
            account_transaction.annotations.extend(annotations)
            account_transaction.description = description
            account_transaction.timestamp = datetime.now()
        else:
            account_transaction = AccountTransaction(
                id=transaction_id,
                account_id=bank_account.id,
                amount=amount,
                state=state,
                annotations=annotations,
                description=description,
                timestamp=datetime.now(),
            )
        session.add(account_transaction)
        await session.commit()


async def update_balance(engine: AsyncEngine, account_number: str) -> None:
    async with AsyncSession(engine) as session:
        bank_account_statement = select(BankAccount)
        bank_account_statement = bank_account_statement.where(
            BankAccount.account_number == account_number
        )
        bank_account_results_exec: ScalarResult[BankAccount] = (
            await session.exec(bank_account_statement)
        )
        bank_account = bank_account_results_exec.one()
        bank_account.balance = await bank_account.calculate_balance(engine)
        session.add(bank_account)
        await session.commit()
