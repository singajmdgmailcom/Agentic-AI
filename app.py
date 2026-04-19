from flask import Flask, render_template, jsonify, request
import json
import os
import time

app = Flask(__name__)

# Import from the anthropic agent architecture
from agent import process_ticket

# We fetch the datasets cleanly
def get_all_tickets():
    path = os.path.join("data", "tickets.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tickets')
def list_tickets():
    tickets = get_all_tickets()
    return jsonify(tickets)

@app.route('/api/ticket/new', methods=['POST'])
def new_ticket():
    data = request.json
    tickets = get_all_tickets()
    
    # Generate new ID continuously
    new_id_num = len(tickets) + 1
    new_id = f"TKT-{str(new_id_num).zfill(3)}"
    
    new_t = {
         "ticket_id": new_id,
         "customer_email": data.get("email"),
         "subject": data.get("subject"),
         "body": data.get("body"),
         "status": "open",
         "source": "web_ui",
         "tier": 1
    }
    tickets.append(new_t)
    
    path = os.path.join("data", "tickets.json")
    with open(path, "w", encoding="utf-8") as f:
         json.dump(tickets, f, indent=4)
         
    return jsonify({"status": "success", "ticket": new_t})

@app.route('/api/run', methods=['POST'])
def run_agent():
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    # Fake fallback for the stunning UI if the user's key crashed or missing.
    if not api_key:
        if os.path.exists('audit_log.json'):
             with open('audit_log.json', 'r', encoding='utf-8') as f:
                 return jsonify({"status": "success", "logs": json.load(f), "fake": True})
        return jsonify({"error": "No API Key and no fallback log found.", "status": "failed"}), 500
        
    tickets = get_all_tickets()
    audit_logs = []
    
    # To prevent rate-limiting Anthropic API keys natively, we force sequential process on Flask backend
    for ticket in tickets:
         if ticket.get("status") in ["resolved", "escalated"]:
             continue
         log = process_ticket(ticket, api_key)
         audit_logs.append(log)
         time.sleep(1) # Prevent 429 errors
                
    # Update the local file for audit constraints
    with open("audit_log.json", "w", encoding="utf-8") as f:
        json.dump(audit_logs, f, indent=4)
        
    return jsonify({"status": "success", "logs": audit_logs, "fake": False})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
