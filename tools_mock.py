import time
import random
import datetime
from data_store import get_order_by_id, get_customer_by_email, get_product_by_id, get_kb_content

class ToolSimulationError(Exception):
    pass

class Tools:
    @staticmethod
    def _simulate_network_delay():
        time.sleep(random.uniform(0.1, 0.5))

    @staticmethod
    def _simulate_failure_chance(chance=0.15):
        if random.random() < chance:
            raise ToolSimulationError("Simulated Service Timeout. Please retry.")

    @staticmethod
    def get_order(order_id: str) -> dict:
        Tools._simulate_network_delay()
        Tools._simulate_failure_chance(0.05)
        
        order = get_order_by_id(order_id)
        if order is None:
            return {"error": f"Order {order_id} not found."}
        return order

    @staticmethod
    def check_refund_eligibility(order_id: str) -> dict:
        Tools._simulate_network_delay()
        Tools._simulate_failure_chance(0.10)
        
        order = get_order_by_id(order_id)
        if order is None:
            return {"error": "Order not found."}
        
        deadline = order.get("return_deadline")
        if not deadline:
             return {"eligible": False, "reason": "No return deadline found or item not shipped yet."}
             
        deadline_date = datetime.datetime.strptime(deadline, "%Y-%m-%d")
        current_date = datetime.datetime(2024, 3, 24) # Aligning to hackathon mock data timeline roughly late march
        
        if current_date > deadline_date:
            return {"eligible": False, "reason": "Return window has expired."}
            
        if order.get("refund_status") == "refunded":
            return {"eligible": False, "reason": "Already refunded."}
            
        return {"eligible": True, "reason": "Within return window."}

    @staticmethod
    def get_customer(email: str) -> dict:
        Tools._simulate_network_delay()
        customer = get_customer_by_email(email)
        if not customer:
            return {"error": "Customer not found."}
        return {"customer_id": customer["customer_id"], "tier": customer.get("tier", 1), "notes": customer.get("notes", "")}

    @staticmethod
    def get_product(product_id: str) -> dict:
        Tools._simulate_network_delay()
        product = get_product_by_id(product_id)
        if not product:
            return {"error": "Product not found."}
        return product

    @staticmethod
    def issue_refund(order_id: str, amount: float) -> dict:
        Tools._simulate_network_delay()
        Tools._simulate_failure_chance(0.05)
        return {"status": "success", "message": f"Refund of {amount} issued for {order_id}."}

    @staticmethod
    def send_reply(ticket_id: str, message: str) -> dict:
        Tools._simulate_network_delay()
        # This signals closure
        return {"status": "resolved", "action": "replied", "message": message}

    @staticmethod
    def escalate(ticket_id: str, summary: str, priority: str) -> dict:
        Tools._simulate_network_delay()
        return {"status": "escalated", "action": "escalated", "summary": summary, "priority": priority}

    @staticmethod
    def search_knowledge_base(query: str) -> dict:
        Tools._simulate_network_delay()
        # We perform a basic sub-string search on the markdown string for simplicity
        kb = get_kb_content().lower()
        query_words = query.lower().split()
        
        score = sum(1 for w in query_words if w in kb)
        if score > 0:
             # Just return the whole text, let LLM summarize it.
             return {"content": get_kb_content()}
        return {"content": "No relevant policy found."}
