import streamlit as st
import json
import os
from agent import process_ticket

# Page Setup
st.set_page_config(page_title="ShopWave Autonomous Support", layout="wide", page_icon="🤖")

st.title("🤖 ShopWave AI - Anthropic Engine")
st.markdown("Powered by **Claude 3.5 Sonnet** (Anthropic) - Resolving complex support queues.")

# Ensure keys
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    api_key = st.text_input("Enter ANTHROPIC_API_KEY", type="password")

# Data loading
if not os.path.exists("data"):
    st.error("Data directory missing! Ensure data files are present.")
    st.stop()

def get_tickets():
    path = os.path.join("data", "tickets.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

original_tickets = get_tickets()

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Queue Stats")
    resolved = len([t for t in original_tickets if t.get("status") == "resolved"])
    escalated = len([t for t in original_tickets if t.get("status") == "escalated"])
    open_t = len(original_tickets) - resolved - escalated
    
    st.metric("Total Tickets", len(original_tickets))
    st.metric("Open Queue", open_t)
    st.metric("Resolved", resolved)
    st.metric("Escalated", escalated)
    
    st.divider()
    
    if st.button("🚀 Process Open Tickets Batch", use_container_width=True):
        if not api_key:
            st.error("Please provide an API Key first.")
        else:
             with st.spinner("Processing batch via Anthropic..."):
                  audit_logs = []
                  for t in original_tickets:
                       if t.get("status") in ["resolved", "escalated"]:
                            continue
                            
                       log = process_ticket(t, api_key)
                       audit_logs.append(log)
                       
                  with open("data/audit_log.json", "w", encoding="utf-8") as file:
                       json.dump(audit_logs, file, indent=4)
                       
                  st.success("Batch Completed!")
                  st.rerun()

with col2:
    st.subheader("Active Knowledge Processing & Tickets")
    
    for t in original_tickets:
        with st.expander(f"Ticket {t.get('ticket_id')} - {t.get('subject', 'No Subject')}"):
             st.write(f"**Customer:** {t.get('customer_email', t.get('customer_id'))}")
             st.write(f"**Status:** {t.get('status', 'Open')}")
             st.write(f"**Issue:** {t.get('body')}")
             if t.get("resolution_note"):
                  st.info(f"Agent Note: {t['resolution_note']}")
