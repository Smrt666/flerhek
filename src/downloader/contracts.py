import json
import time

import requests

# API Endpoints
CONTRACT_LIST_URL = "https://flare-explorer.flare.network/api?module=contract&action=listcontracts&filter=verified&page={}"
CONTRACT_SOURCE_URL = "https://flare-explorer.flare.network/api?module=contract&action=getsourcecode&address={}"

# API Rate Limit
RATE_LIMIT = 0.1

# Contracts Directory
DATA_FILE = "../data/contracts.json"


def fetch_verified_contracts():
    """Fetches all verified contracts from Flare Explorer API across multiple pages."""

    addresses = []
    page = 0

    while True:
        response = requests.get(CONTRACT_LIST_URL.format(page))

        if response.status_code != 200:
            print(f"Failed to fetch page {page}, status code {response.status_code}")
            break

        data = response.json()

        if data.get("status") != "1" or not data.get("result"):
            break

        addresses.extend(contract["Address"] for contract in data["result"])
        print(f"Fetched {len(data['result'])} contracts from page {page}")

        page += 1
        time.sleep(RATE_LIMIT)

    return addresses


def fetch_contract_data(address):
    """Fetches source code and metadata for a given contract address."""

    response = requests.get(CONTRACT_SOURCE_URL.format(address))

    if response.status_code != 200:
        print(
            f"Failed to fetch source for {address}, status code {response.status_code}"
        )
        return None

    data = response.json()

    if data.get("status") != "1" or not data.get("result"):
        return None

    return data["result"][0]


def main():
    """Main execution function."""

    print("Fetching contract list...")
    addresses = fetch_verified_contracts()

    if not addresses:
        print("No contracts found")
        return

    print(f"Found {len(addresses)} contracts")

    contracts = []

    for address in addresses:
        print(f"Fetching source for contract at {address}...")
        data = fetch_contract_data(address)
        if data:
            contracts.append(data)

        time.sleep(RATE_LIMIT)

    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(contracts, file, indent=4)


if __name__ == "__main__":
    main()
