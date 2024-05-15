#!/usr/bin/env python3
import random
from decimal import Decimal

from faker import Faker

fake = Faker()


def generate_bank_account() -> dict[str, str | Decimal]:
    name = fake.name()
    account_number = "".join([str(random.randint(0, 9)) for _ in range(16)])
    state = random.choice(["Active", "Cancelled"])
    balance: Decimal = Decimal(round(random.uniform(0, 10000), 2))
    return {
        "name": name,
        "account_number": account_number,
        "state": state,
        "balance": balance,
    }
