import streamlit as st
import json
from agent_logic import run_complaint_agent

st.set_page_config(page_title="AI Complaint Resolution Agent", page_icon="🤖", layout="wide")

st.title("🤖 AI Complaint Resolution Agent")
st.markdown("### Real-World Problem: Businesses need consistent complaint triage and resolution.")
st.divider()

# Example user request from the slide
default_text = "My order is 10 days late. I contacted support twice without a response. Order ID is 1001."

with st.form("complaint_form"):
    user_input = st.text_area("Enter Customer Complaint:", value=default_text, height=100)
    submit_button = st.form_submit_button("Resolve Complaint")

if submit_button:
    if not user_input.strip():
        st.warning("Please enter a complaint.")
    else:
        with st.spinner("Agent is analyzing the complaint, checking databases, and drafting a response..."):
            try:
                # Run the CrewAI agent
                result = run_complaint_agent(user_input)
                
                # The result from CrewAI is usually a string. We need to parse the JSON from it.
                # Sometimes LLMs wrap JSON in ```json ... ```, so we strip that.
                raw_output = result.raw.strip()
                if raw_output.startswith("```json"):
                    raw_output = raw_output[7:-3]
                elif raw_output.startswith("```"):
                    raw_output = raw_output[3:-3]
                
                parsed_data = json.loads(raw_output)
                
                # Display Output exactly as required by the slide
                st.success("✅ Complaint Resolved!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Category:** {parsed_data.get('category', 'N/A')}")
                with col2:
                    st.warning(f"**Priority:** {parsed_data.get('priority', 'N/A')}")
                
                st.subheader("📝 Proposed Resolution")
                st.write(parsed_data.get('proposed_resolution', 'N/A'))
                
                st.subheader("✉️ Drafted Customer Reply")
                st.text_area("Copy and send this:", value=parsed_data.get('reply', 'N/A'), height=200)
                
                st.subheader("🎫 Internal Support Ticket")
                st.text_area("Ticket Notes:", value=parsed_data.get('ticket', 'N/A'), height=150)
                
            except json.JSONDecodeError:
                st.error("The agent did not return valid JSON. Here is the raw output:")
                st.write(result)
            except Exception as e:
                st.error(f"An error occurred: {e}")
