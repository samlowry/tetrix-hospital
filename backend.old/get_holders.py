import requests
import sys
import time


def fetch_top_jetton_holders(jetton_address, limit=1000, offset=0):
    API_ENDPOINT = "https://toncenter.com/api/v3/jetton/wallets"

    try:
        response = requests.get(
            API_ENDPOINT,
            params={
                "jetton_address": jetton_address,
                "exclude_zero_balance": "true",
                "limit": limit,
                "offset": offset,
                "sort": "desc"
            },
            headers={"accept": "application/json"}
        )
        response.raise_for_status()

        data = response.json()
        holders = data.get("jetton_wallets", [])
        address_book = data.get("address_book", {})

        # Map both wallet and owner addresses to user_friendly names
        for holder in holders:
            wallet_address = holder['address']
            owner_address = holder['owner']
            
            holder['wallet_friendly'] = address_book.get(wallet_address, {}).get('user_friendly', wallet_address)
            holder['owner_friendly'] = address_book.get(owner_address, {}).get('user_friendly', owner_address)

        return holders

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        return []


if __name__ == "__main__":
    JETTON_ADDRESS = "EQC-OHxhI9r5ojKf6QMLFjhQrKoawN1thhHFCvImINhfK40C"
    BATCH_SIZE = 1000
    
    all_holders = []
    offset = 0
    headers_printed = False
    
    while True:
        print(f"Fetching batch with offset {offset}...", file=sys.stderr)
        holders = fetch_top_jetton_holders(JETTON_ADDRESS, limit=BATCH_SIZE, offset=offset)
        
        if not holders:
            break
            
        all_holders.extend(holders)
        
        # Get fields from first batch
        if not headers_printed and holders:
            fields = sorted(holders[0].keys())
            print('\t'.join(fields))
            headers_printed = True
            
        # Print batch data
        for holder in holders:
            row = [str(holder.get(field, 'N/A')) for field in fields]
            print('\t'.join(row))
            
        if len(holders) < BATCH_SIZE:
            break
            
        offset += BATCH_SIZE
        time.sleep(1)  # 1 second delay between requests
    
    print(f"Total holders processed: {len(all_holders)}", file=sys.stderr)
