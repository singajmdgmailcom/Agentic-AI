# Architecture: ShopWave Core Agent

## System Design and ReAct Loop

```mermaid
graph TD
    A[Ticket Queue] --> B[main.py ThreadPoolExecutor]
    B -->|Thread Spawn| C[agent.py ReAct Loop]
    C --> D{Evaluate State}
    D -->|New Action Needed| E[LLM Inference gemini-2.5-pro]
    E --> F{Tool Call?}
    F -->|Yes| G[Execute Tool via tools_mock.py]
    G --> H{Execution Success?}
    H -->|Yes| I[Append context and loop back]
    H -->|No Network Error| J[Wait/Backoff & Retry Function]
    I --> D
    J --> G
    
    F -->|No Action / Terminate| K[Record Audit Log]
    D -->|Ticket Escalated| K
    D -->|Ticket Resolved| K
    
    K --> L[Save to audit_log.json]

    # Tool Subsystem
    subgraph tools_mock.py [Simulated Tool Integrations]
    T1(get_order)
    T2(get_customer)
    T3[check_refund_eligibility]
    T4(issue_refund)
    T5(search_knowledge_base)
    end
    
    G -.-> tools_mock.py
```

## State Management
- **In-Memory Thread Mapping**: The `main.py` generates native Python thread workers which manage their own `audit` tracking dictionary in memory. This eliminates dead-locks and ensures tickets process independently sequentially over the execution timeline.
- **Context Accumulation**: The agent pushes its actions and the tool results into the `messages` array fed into `gemini-2.5-pro` forming an isolated "session state" mimicking memory allowing it to read previous tool responses within the context limit without database overhead.
- **LLM Rate-Limiter Tuning**: The thread pool max workers are constrained to 10 preventing instant 429 API blocks across the mock sample structure.
