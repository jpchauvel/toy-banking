#!/usr/bin/env python3
from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import Column, Engine, String
from sqlmodel import Field, SQLModel, Session, create_engine, select

from fake import generate_bank_account


class BankAccount(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True
    )
    name: str
    account_number: str = Field(
        sa_column=Column("account_number", String, unique=True)
    )
    state: str

    def calculate_balance(self, engine: Engine) -> Decimal:
        with Session(engine) as session:
            account_transactions = session.exec(
                select(AccountTransaction).where(
                    AccountTransaction.account_id == self.id
                )
            ).all()
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


def get_engine(database_url: str) -> Engine:
    engine: Engine = create_engine(database_url)
    SQLModel.metadata.create_all(engine)
    return engine


def create_db(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)


def reset_accounts(engine: Engine, num_fake_accounts: int) -> None:
    """Generate bank accounts."""
    # Reset database if flag set
    with Session(engine) as session:
        bank_account_statement = select(BankAccount)
        bank_account_results = session.exec(bank_account_statement).all()
        account_transaction_statement = select(AccountTransaction)
        account_transaction_results = session.exec(
            account_transaction_statement
        ).all()
        [session.delete(row) for row in bank_account_results]
        [session.delete(row) for row in account_transaction_results]

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
        with Session(engine) as session:
            session.add(account)
            session.add(account_transaction)
            session.commit()
