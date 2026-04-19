# Hackathon 2026 - Autonomous Support Resolution Agent

This repository contains the submission for the 2026 Global Agentic AI Hackathon.

## Setup Instructions

1. **Clone the repository.**
2. **Install requirements:**
    ```powershell
    pip install -r requirements.txt
    ```
3. **Set API Key:**
    Export your Google Gemini API Key. This agent utilizes `gemini-2.5-pro` for strong reasoning capabilities matching the hackathon's complexity constraints.
    ```powershell
    $env:GOOGLE_API_KEY="your_api_key_here"
    ```
4. **Run the Agent:**
    ```powershell
    python main.py
    ```
    This single command will download the mock data files directly into `./data/`, initialize the ReAct loop across 20 concurrent threads, and generate the final `audit_log.json`.

## Tech Stack
* **Language**: Python 3
* **LLM Engine**: Google GenAI SDK (`gemini-2.5-pro`)
* **Orchestration**: Custom ReAct loop using Function Calling with manual Retry/Backoff algorithms.
* **Concurrency**: Python's native `concurrent.futures.ThreadPoolExecutor`
* **Data Layer**: Mocked in-memory dictionary caching (simulated with latency and exceptions).

## Agent Design Highlights
* **Concurrency Strategy**: The tickets are processed using a thread-pool of 10 workers mapped to the `process_ticket` function to prevent sequential bottlenecks.
* **Failure Resiliency**: The `tools_mock.py` inherently fails randomly simulating real conditions. The agent loop naturally catches `ToolSimulationError` exceptions and implements sleep/backoff before retrying execution rather than dropping the ticket.
* **Schema Safety**: Function tools automatically enforce strict type dictionaries.
