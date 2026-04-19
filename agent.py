import json
import anthropic
import os
import tools

SYSTEM_INSTRUCTION = """
You are an autonomous customer support agent for ShopWave.
Your goal is to resolve support tickets via function calling.

STRICT Directives:
1. You must step-by-step reason before making decisions.
2. ALWAYS call get_customer first to verify tier.
3. Apply tier-based leniency: VIP > Premium > Standard.
4. Escalate if refund > $200 OR if it's a warranty claim OR if you are uncertain.
5. End every resolution with a customer-friendly message.
6. Once finished, you MUST call 'update_ticket' with your final 'status' (resolved or escalated) and a 'resolution_note'.
7. Rate your confidence (0.0 to 1.0) inside your response. If confidence < 0.6, auto-escalate.
"""

def process_ticket(ticket_data: dict, api_key: str):
    if not api_key:
         return {"error": "No ANTHROPIC_API_KEY provided."}
         
    client = anthropic.Anthropic(api_key=api_key)
    
    # Define Anthropic Tools schema mapping to tools.py
    anthropic_tools = [
        {
            "name": "get_customer",
            "description": "returns customer name, email, tier, notes",
            "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}
        },
        {
            "name": "get_order",
            "description": "returns order details, status, delivery date, items",
            "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}
        },
        {
            "name": "get_product",
            "description": "returns product name, category, warranty period",
            "input_schema": {"type": "object", "properties": {"product_id": {"type": "string"}}, "required": ["product_id"]}
        },
        {
            "name": "list_customer_tickets",
            "description": "returns all tickets for a customer",
            "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}
        },
        {
            "name": "check_refund_eligibility",
            "description": "checks policy rules",
            "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}, "reason": {"type": "string"}}, "required": ["order_id", "reason"]}
        },
        {
            "name": "update_ticket",
            "description": "marks ticket as resolved/escalated",
            "input_schema": {
                 "type": "object", 
                 "properties": {
                      "ticket_id": {"type": "string"}, 
                      "status": {"type": "string", "enum": ["resolved", "escalated"]},
                      "resolution_note": {"type": "string"}
                 }, 
                 "required": ["ticket_id", "status", "resolution_note"]
            }
        },
        {
            "name": "search_knowledge_base",
            "description": "returns relevant policy sections",
            "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
        }
    ]

    messages = [
        {
            "role": "user",
            "content": f"Ticket Information: {json.dumps(ticket_data)}"
        }
    ]
    
    audit_trace = []
    MAX_TURNS = 10
    
    for turn in range(MAX_TURNS):
        response = client.messages.create(
            model="claude-3-5-sonnet-latest",
            system=SYSTEM_INSTRUCTION,
            max_tokens=1000,
            messages=messages,
            tools=anthropic_tools
        )
        
        # Pull out assistant reasoning and tool use blocks
        assistant_blocks = []
        tool_invocations = []
        
        for content_block in response.content:
            if content_block.type == 'text':
                audit_trace.append({"role": "model_reasoning", "content": content_block.text})
                assistant_blocks.append({"type": "text", "text": content_block.text})
            elif content_block.type == 'tool_use':
                tool_invocations.append(content_block)
                assistant_blocks.append({
                     "type": "tool_use",
                     "id": content_block.id,
                     "name": content_block.name,
                     "input": content_block.input
                })

        messages.append({
             "role": "assistant",
             "content": assistant_blocks
        })

        if not tool_invocations:
             # Stop Condition
             audit_trace.append({"role": "system", "content": "Agent voluntarily stopped without more tools."})
             break
             
        # Execute tools
        tool_results = []
        for tool_use in tool_invocations:
             func_name = tool_use.name
             kwargs = tool_use.input
             
             try:
                 func = getattr(tools, func_name)
                 result = func(**kwargs)
             except Exception as e:
                 result = {"error": str(e)}
                 
             audit_trace.append({"role": "tool_execution", "tool": func_name, "args": kwargs, "result": result})
             
             tool_results.append({
                  "type": "tool_result",
                  "tool_use_id": tool_use.id,
                  "content": json.dumps(result)
             })
             
        messages.append({
             "role": "user",
             "content": tool_results
        })
        
        # Check if ticket was updated implying termination
        if any(t.name == "update_ticket" for t in tool_invocations):
             break
             
    # Calculate confidence based off text blocks implicitly required by prompt
    # Not full proof but works for demo
    
    return {
         "ticket_id": ticket_data.get("ticket_id", "Unknown"),
         "trace": audit_trace,
         "final_messages": messages
    }
