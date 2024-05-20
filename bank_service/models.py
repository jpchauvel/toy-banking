#!/usr/bin/env python3
from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import Column, MetaData, String, ScalarResult
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlmodel import Field, SQLModel, select
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


class BankAccount(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True
    )
    name: str
    account_number: str = Field(
        sa_column=Column("account_number", String, unique=True)
    )
    state: str

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
            balance = Decimal(0)
            for account_transaction in account_transactions:
                balance += account_transaction.amount
            return balance


class AccountTransaction(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True
    )
    account_id: uuid.UUID = Field(foreign_key="bankaccount.id")
    amount: Decimal = Field(default=0, max_digits=9, decimal_places=2)
    description: str
    timestamp: datetime


async def reset_accounts(engine: AsyncEngine, num_fake_accounts: int) -> None:
    """Generate bank accounts."""
    # Reset database if flag set
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

    # Generate new bank accounts
    for _ in range(num_fake_accounts):
        account_data: dict[str, str | Decimal] = generate_bank_account()
        balance: Decimal = account_data.pop("balance")
        account: BankAccount = BankAccount(**account_data)
        account_transaction: AccountTransaction = AccountTransaction(
            account_id=account.id,
            amount=balance,
            description="Initial deposit",
            timestamp=datetime.now(),
        )
        async with AsyncSession(engine) as session:
            session.add(account)
            session.add(account_transaction)
            await session.commit()
