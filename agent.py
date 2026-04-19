import json
from data_store import get_order_by_id, get_customer_by_email, get_product_by_id, get_all_tickets
import data_store
from tools_mock import Tools, ToolSimulationError
from google import genai
from google.genai import types
import os
import time

def setup_client():
    # Will throw exception if GOOGLE_API_KEY is not set. Assuming the user will set it.
    try:
         return genai.Client()
    except Exception as e:
         print(f"Error initializing Gemini client. Did you set GOOGLE_API_KEY? {e}")
         return None

SYSTEM_INSTRUCTION = """
You are an autonomous support resolution agent for ShopWave. You have the ability to read customer, order, and product data, check knowledge bases, and take actions such as issuing refunds, sending replies, or escalating to human agents.

Your goal is to autonomously resolve customer support tickets using the available tools. 

Constraints:
1.  **Explain your reasoning for EVERY action.**
2.  Be smart about edge cases: e.g. check for exceptions (VIP tiers) if return windows pass. 
3.  If an order or customer does not exist, ask for clarifying information by sending a reply, DO NOT hallucinate.
4.  If a tool returns an error or timeout, backoff and retry gracefully.
5.  If you issue a refund, you MUST use the `issue_refund` tool AFTER checking eligibility. 
6.  Once you have fulfilled the request or handled the issue, you MUST call `send_reply` or `escalate` to signal ticket closure.
"""

def extract_json_from_response(text):
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
         text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())

def process_ticket(ticket, client):
    """
    Main ReAct loop for a single ticket.
    Returns the audit log dictionary.
    """
    if not client:
        return {"ticket_id": ticket["ticket_id"], "error": "No API client"}

    audit = {
        "ticket_id": ticket["ticket_id"],
        "steps": [],
        "outcome": None
    }
    
    # Initialize chat context
    messages = [
        {"role": "user", "parts": [
            types.Part.from_text(text=f"Ticket ID: {ticket['ticket_id']}\nCustomer Email: {ticket['customer_email']}\nSubject: {ticket['subject']}\nBody: {ticket['body']}")
        ]}
    ]

    tool_declarations = [
        types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name="get_order",
                description="Lookup order details, status, timestamps",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"order_id": types.Schema(type=types.Type.STRING)},
                    required=["order_id"]
                )
            ),
            types.FunctionDeclaration(
                 name="check_refund_eligibility",
                 description="Checks if an order is eligible for refund.",
                 parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"order_id": types.Schema(type=types.Type.STRING)},
                    required=["order_id"]
                )
            ),
             types.FunctionDeclaration(
                 name="get_customer",
                 description="Lookup customer profile, tier, and internal notes",
                 parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"email": types.Schema(type=types.Type.STRING)},
                    required=["email"]
                )
            ),
            types.FunctionDeclaration(
                 name="get_product",
                 description="Product metadata, category, warranty info",
                 parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"product_id": types.Schema(type=types.Type.STRING)},
                    required=["product_id"]
                )
            ),
            types.FunctionDeclaration(
                 name="search_knowledge_base",
                 description="Search standard return policies and FAQs",
                 parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"query": types.Schema(type=types.Type.STRING)},
                    required=["query"]
                )
            ),
            types.FunctionDeclaration(
                 name="issue_refund",
                 description="WARNING: Irreversible. Issues a refund. MUST check eligibility first.",
                 parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "order_id": types.Schema(type=types.Type.STRING),
                        "amount": types.Schema(type=types.Type.NUMBER)
                    },
                    required=["order_id", "amount"]
                )
            ),
            types.FunctionDeclaration(
                 name="send_reply",
                 description="Sends a reply back to the customer. CLOSES the ticket.",
                 parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "ticket_id": types.Schema(type=types.Type.STRING),
                        "message": types.Schema(type=types.Type.STRING)
                    },
                    required=["ticket_id", "message"]
                )
            ),
             types.FunctionDeclaration(
                 name="escalate",
                 description="Routes ticket to human support. CLOSES the ticket.",
                 parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "ticket_id": types.Schema(type=types.Type.STRING),
                        "summary": types.Schema(type=types.Type.STRING),
                        "priority": types.Schema(type=types.Type.STRING)
                    },
                    required=["ticket_id", "summary", "priority"]
                )
            )
        ])
    ]

    max_steps = 15
    steps = 0
    resolved = False
    
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=tool_declarations,
        temperature=0.0
    )
    
    while steps < max_steps and not resolved:
        steps += 1
        
        # LLM Interaction
        try:
             # Retry budget wrapper for LLM API calls just in case
             response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=messages,
                config=config
             )
        except Exception as e:
              messages.append({"role": "user", "parts": [types.Part.from_text(text=f"System error hitting LLM: {str(e)}")]})
              time.sleep(2) # Backoff
              continue
              
        if response.candidates and response.candidates[0].content:
            msg_content = response.candidates[0].content
            
            # Record reasoning block implicitly if LLM speaks it before function call
            if msg_content.parts and msg_content.parts[0].text:
                 audit["steps"].append({"type": "reasoning", "content": msg_content.parts[0].text})
            
            # Map the message into the array
            messages.append({"role": "model", "parts": msg_content.parts})
            
            function_calls = [p.function_call for p in msg_content.parts if p.function_call]
            
            if not function_calls:
                 # If no function call is made, prompt to force closure.
                 messages.append({"role": "user", "parts": [types.Part.from_text(text="You MUST use either 'send_reply' or 'escalate' to close out the ticket once you are finished. Please do so.")]})
                 continue
                 
            for call in function_calls:
                 func_name = call.name
                 args = call.args
                 
                 audit_step = {
                     "type": "tool_call",
                     "function": func_name,
                     "arguments": args,
                 }
                 
                 # Map string name to python function execution
                 retries = 3
                 tool_output = None
                 while retries > 0:
                     try:
                         func_ref = getattr(Tools, func_name)
                         
                         if func_name in ["get_order", "check_refund_eligibility"]:
                             tool_output = func_ref(args["order_id"])
                         elif func_name == "get_customer":
                             tool_output = func_ref(args["email"])
                         elif func_name == "get_product":
                              tool_output = func_ref(args["product_id"])
                         elif func_name == "search_knowledge_base":
                              tool_output = func_ref(args["query"])
                         elif func_name == "issue_refund":
                              tool_output = func_ref(args["order_id"], float(args["amount"]))
                         elif func_name == "send_reply":
                              tool_output = func_ref(args["ticket_id"], args["message"])
                              resolved = True
                         elif func_name == "escalate":
                              tool_output = func_ref(args["ticket_id"], args["summary"], args["priority"])
                              resolved = True
                         break # Success
                     except ToolSimulationError as e:
                         retries -= 1
                         print(f"[{ticket['ticket_id']}] Tool {func_name} failed. Retries left: {retries}")
                         if retries == 0:
                              tool_output = {"error": f"Tool {func_name} timed out repeatedly."}
                         else:
                              time.sleep(1) # simulate backoff
                     except Exception as e:
                         tool_output = {"error": f"Tool execution crashed: {str(e)}"}
                         break
                         
                 audit_step["result"] = tool_output
                 audit["steps"].append(audit_step)
                 
                 messages.append({"role": "user", "parts": [types.Part.from_function_response(name=func_name, response={"result": tool_output})] })
                 
                 if resolved:
                     audit["outcome"] = audit_step["result"]
                     break # Exit function execution loop
        else:
             break # No valid response

    if not resolved:
         audit["outcome"] = {"status": "failed", "reason": "Max steps exceeded or LLM crashed."}
         
    return audit
