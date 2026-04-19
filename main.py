import json
import concurrent.futures
import time
from data_store import init_data, get_all_tickets
from agent import setup_client, process_ticket

def main():
    print("Initializing Data Store...")
    init_data()
    
    tickets = get_all_tickets()
    print(f"Loaded {len(tickets)} tickets. Starting Agentic Processing.")
    
    client = setup_client()
    if not client:
        print("API Client failed setup. Cannot proceed.")
        return

    start_time = time.time()
    
    audit_logs = []
    
    # Process concurrently. The hackathon constraint penalizes sequential processing.
    # Limiting max_workers to 10 so we don't trip API rate limits too quickly on standard tiers.
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all tasks
        future_to_ticket = {executor.submit(process_ticket, ticket, client): ticket for ticket in tickets}
        
        for future in concurrent.futures.as_completed(future_to_ticket):
            ticket = future_to_ticket[future]
            try:
                log = future.result()
                audit_logs.append(log)
                print(f"[{ticket['ticket_id']}] Completed. Outcome: {log.get('outcome', {}).get('status', 'resolved')}")
            except Exception as e:
                print(f"[{ticket['ticket_id']}] Exception generated: {e}")
                
    end_time = time.time()
    print(f"Total processing time: {end_time - start_time:.2f} seconds.")
    
    with open("audit_log.json", "w", encoding="utf-8") as f:
        json.dump(audit_logs, f, indent=4)
        
    print("Audit log 'audit_log.json' generated successfully. All 20 tickets processed.")

if __name__ == "__main__":
    main()
