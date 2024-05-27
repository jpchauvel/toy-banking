import random
from decimal import Decimal

from faker import Faker

fake: Faker = Faker()


def generate_bank_account() -> dict[str, str | Decimal]:
    name: str = fake.name()
    account_number: str = "".join(
        [str(random.randint(0, 9)) for _ in range(16)]
    )
    state: str = random.choice(["active", "canceled"])
    balance: Decimal = Decimal(round(random.uniform(0, 10000), 2))
    return {
        "name": name,
        "account_number": account_number,
        "state": state,
        "balance": balance,
    }
