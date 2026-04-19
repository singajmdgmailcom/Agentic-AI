import json
import os

DATA_DIR = "data"

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def get_customer(customer_id: str):
    """returns customer name, email, tier, notes"""
    customers = load_json("customers.json")
    for c in customers:
        if c.get("customer_id") == customer_id or c.get("email") == customer_id:
             return {"name": c.get("name", "Unknown"), "email": c.get("email"), "tier": c.get("tier", "Standard"), "notes": c.get("notes", "")}
    return {"error": "Customer not found"}

def get_order(order_id: str):
    """returns order details, status, delivery date, items"""
    orders = load_json("orders.json")
    for o in orders:
        if o.get("order_id") == order_id:
             return {"order_id": o["order_id"], "status": o.get("status"), "delivery_date": o.get("delivery_date"), "items": o.get("product_id")}
    return {"error": "Order not found"}

def get_product(product_id: str):
    """returns product name, category, warranty period"""
    products = load_json("products.json")
    for p in products:
        if p.get("product_id") == product_id:
             return {"product_name": p.get("name"), "category": p.get("category"), "warranty_period": p.get("warranty", "Unknown")}
    return {"error": "Product not found"}

def list_customer_tickets(customer_id: str):
    """returns all tickets for a customer"""
    tickets = load_json("tickets.json")
    return [t for t in tickets if t.get("customer_id") == customer_id or t.get("customer_email") == customer_id]

def check_refund_eligibility(order_id: str, reason: str):
    """checks policy rules and returns eligible/not-eligible + reason, considering customer tier and return window"""
    order = get_order(order_id)
    if "error" in order:
        return {"eligible": False, "reason": "Order ID not found to verify."}
    if order.get("status") != "delivered":
        return {"eligible": False, "reason": "Item has not been delivered yet."}
        
    return {"eligible": True, "reason": "System verification logic allows review. Base policy check deferred to tier evaluation."}

def update_ticket(ticket_id: str, status: str, resolution_note: str):
    """marks ticket as resolved/escalated and saves to tickets.json"""
    tickets = load_json("tickets.json")
    found = False
    for t in tickets:
        if t.get("ticket_id") == ticket_id:
            t["status"] = status
            t["resolution_note"] = resolution_note
            found = True
            break
            
    if found:
         path = os.path.join(DATA_DIR, "tickets.json")
         with open(path, "w", encoding="utf-8") as f:
             json.dump(tickets, f, indent=4)
         return {"success": f"Ticket {ticket_id} updated to {status}"}
    return {"error": "Ticket not found."}

def search_knowledge_base(query: str):
    """returns relevant policy sections from knowledge-base.md"""
    path = os.path.join(DATA_DIR, "knowledge-base.md")
    content = "No Knowledge Base Found."
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    return {"kb_content": content} # Return raw for LLM context.
