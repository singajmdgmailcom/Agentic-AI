# Failure Mode Analysis

As per the constraints for building real-world AI applications, the autonomous agent explicitly anticipates common fault tolerances bridging external APIs, user intent, and inference models.

### Scenario 1: Transient Service Outages (Timeout Injection)

#### The Problem: 
External API gateways are inherently unreliable. Random network latency spikes or explicit `504 Gateway Timeouts` commonly crash deterministic scripts. In the hackathon context, `tools_mock.py` inherently injects a 5% to 15% `ToolSimulationError` failure chance whenever a tool is called.

#### Agent Handling:
The ReAct controller loop (`agent.py`) actively bounds the tool execution wrapper inside a Retry block with a budget of 3 retries.
```python
except ToolSimulationError as e:
    retries -= 1
    if retries == 0:
        tool_output = {"error": f"Tool {func_name} timed out repeatedly."}
    else:
        time.sleep(1) # simulate backoff
```
The agent maintains its context window and doesn't crash if an API node drops randomly, preserving the state of the ticket resolution.

---

### Scenario 2: Hallucination and Unstructured Ambiguous Requests

#### The Problem: 
A customer submits a completely ambiguous request with no order ID ("my thing is broken pls help" - Ticket 20). If left unchecked, the model might hallucinate an `order_id` or default to a system failure exception.

#### Agent Handling:
The agent evaluates the input state against its base directives. Since no `order_id` entity is present, it explicitly triggers the fallback condition built into the system prompt:
`If an order or customer does not exist, ask for clarifying information by sending a reply, DO NOT hallucinate.`
The agent identifies the absence of the order ID and immediately resolves the execution loop by calling `send_reply` querying the user for their order details. The conversation loop is safely exited.

---

### Scenario 3: Social Engineering & Policy Evasion

#### The Problem: 
Customers attempting to bypass policy (Ticket 18 - pretending to be Premium without eligibility).
In primitive bot designs, recognizing authority intent forces action.

#### Agent Handling:
The agent first utilizes `get_customer` to verify the actual tier matching the email input. Discovering a tier mismatch compared to the claim (Tier 1 vs Premium assertion), the model evaluates the `check_refund_eligibility` tool to verify technical expiration limits. Validating that policy overrules text-based assertions, the agent denies the claim with strict parameters preventing logic abuse and utilizes `send_reply` to formally reject the social engineering attempt.
