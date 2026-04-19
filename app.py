from flask import Flask, render_template, jsonify
import json
import os
import time

app = Flask(__name__)

# Import from existing architecture
from data_store import init_data, get_all_tickets
from agent import setup_client, process_ticket
import concurrent.futures

# Initialize data store
init_data()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tickets')
def list_tickets():
    tickets = get_all_tickets()
    return jsonify(tickets)

@app.route('/api/run', methods=['POST'])
def run_agent():
    # If the user doesn't have an API key locally loaded, we fallback to the mocked audit log
    # purely for presentation purposes if the LLM crashes.
    client = setup_client()
    if not client:
        if os.path.exists('audit_log.json'):
             with open('audit_log.json', 'r', encoding='utf-8') as f:
                 return jsonify({"status": "success", "logs": json.load(f), "fake": True})
        return jsonify({"error": "No API Key and no fallback log found.", "status": "failed"}), 500
        
    tickets = get_all_tickets()
    audit_logs = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_ticket = {executor.submit(process_ticket, ticket, client): ticket for ticket in tickets}
        for future in concurrent.futures.as_completed(future_to_ticket):
            try:
                log = future.result()
                audit_logs.append(log)
            except Exception as e:
                pass
                
    # Update the local file for audit constraints
    with open("audit_log.json", "w", encoding="utf-8") as f:
        json.dump(audit_logs, f, indent=4)
        
    return jsonify({"status": "success", "logs": audit_logs, "fake": False})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
