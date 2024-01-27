import requests
import traceback
from retrying import retry
import datetime

# Solana RPC endpoint
solana_rpc_url = "https://api.mainnet-beta.solana.com"
solana_rpc_url_quicknode = "" # better to have other rpc than mainnet beta

# Specific key to monitor
target_key = "reg8X1V65CSdmrtEjMgnXZk96b9SUSQrJ8n1rP1ZMg7"


# Define a retry decorator with desired settings
@retry(
    stop_max_attempt_number=3,   # Maximum number of retry attempts
    wait_fixed=1000,             # Wait 1 second between retries
    retry_on_exception=lambda x: isinstance(x, (requests.exceptions.RequestException))
)
def make_http_request(url, params):
    try:
        response = requests.post(url, json=params)
        response.raise_for_status()  # Raise an exception for non-2xx HTTP responses
        return response.json()
    except requests.exceptions.RequestException as e:
        # Raise the exception to trigger retry
        raise e
    
def get_recent_transactions(account_address):
    # Get recent transactions for the specified account address
    params = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getConfirmedSignaturesForAddress2",
        "params": [account_address, {"limit": 100}]  # Adjust limit
    }
    response = make_http_request(solana_rpc_url, params)
    return response["result"]

def get_transaction_details(transaction_id):
    # Get transaction details by transaction ID
    params = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [transaction_id, {"encoding": "jsonParsed"}]
    }
    response = make_http_request(solana_rpc_url_quicknode, params)
    return response["result"]

def main():
    while True:
        try:
            transactions = get_recent_transactions(target_key)
            for transaction in transactions:
                transaction_id = transaction["signature"]
                details = get_transaction_details(transaction_id)
                program_logs = details.get("meta", {}).get("logMessages", [])

                for log in program_logs:
                    if "Program log: Reject" in log:
                        all_accounts = details["transaction"]["message"]["accountKeys"]
                        requied_account = ''

                        for acc in all_accounts:
                            if acc["pubkey"].lstrip().startswith("Adminz") or acc["pubkey"].lstrip().startswith("reg8X1"):
                                continue
                            
                            requied_account = acc["pubkey"]
                            break

                        acc_transactions = get_recent_transactions(requied_account)
                        oldest_acc = sorted(acc_transactions, key=lambda x: x["blockTime"])[0]
                        trx_id = oldest_acc["signature"]
                        trx_details = get_transaction_details(trx_id)

                        program_logs_2 = trx_details.get("meta", {}).get("logMessages", [])
                        rejected_date_time = datetime.datetime.fromtimestamp(transaction["blockTime"])
                        applied_date_time = datetime.datetime.fromtimestamp(trx_details["blockTime"])

                        for log in program_logs_2:
                            if "Program log: Apply" in log:
                                participated_accounts = trx_details["transaction"]["message"]["instructions"][1]["accounts"]

                                sfdp_participant = participated_accounts[0]
                                mainnet_identity = participated_accounts[1]
                                testnet_identity = participated_accounts[2]

                                print(f"mainnet: {mainnet_identity}, testnet: {testnet_identity}, participation_pubkey: {sfdp_participant}, rejection_date: {rejected_date_time}, applied_date:{applied_date_time}")
        except Exception as e:
            print("Error:", str(e))
            traceback.print_exc()
            break

        #time.sleep(60)  # Adjust the polling interval as needed

if __name__ == "__main__":
    main()
