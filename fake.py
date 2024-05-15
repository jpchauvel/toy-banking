#!/usr/bin/env python3
import argparse
from faker import Faker
import random
from typing import Dict, List

fake = Faker()


def generate_bank_account() -> Dict[str, str | float]:
    name = fake.name()
    account_number = "".join([str(random.randint(0, 9)) for _ in range(16)])
    state = random.choice(["Active", "Cancelled"])
    balance = round(random.uniform(0, 10000), 2)
    return {
        "name": name,
        "account_number": account_number,
        "state": state,
        "balance": balance,
    }


def main(num_accounts: int) -> None:
    bank_accounts: List[Dict[str, str | float]] = [
        generate_bank_account() for _ in range(num_accounts)
    ]

    # Print the generated bank accounts
    for account in bank_accounts:
        print(account)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate bank accounts")
    parser.add_argument(
        "-n",
        "--num-accounts",
        type=int,
        default=10,
        help="Number of bank accounts to generate",
    )
    args = parser.parse_args()

    main(args.num_accounts)
