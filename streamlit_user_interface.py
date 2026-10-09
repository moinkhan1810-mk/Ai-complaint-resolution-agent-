import os
import json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from agent import process_complaint
from models import ComplaintAnalysisResult
from tools import send_customer_email

st.set_page_config(
    page_title="AI Complaint Resolution Agent",
    page_icon="🤖",
    layout="wide"
)

# Fetch API Key from Streamlit Secrets or environment variables
groq_api_key = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))

# Sidebar Setup
with st.sidebar:
    st.title("🤖 Resolution Agent")
    st.markdown("**Powered by CrewAI & Groq** (`llama-3.3-70b-versatile`)")
    st.markdown("---")
    
    st.subheader("Supported Categories")
    st.markdown("- 🚚 Late Deliveries\n- 📦 Damaged Products\n- 🔄 Refunds & Returns\n- ❓ Missing Items\n- ❌ Cancellations\n- 💳 Payment Issues")
    st.markdown("---")
    
    st.subheader("Sample Order Database")
    st.code(
        "ORD-1001 | Delayed (10 days past)\n"
        "ORD-1002 | Delivered\n"
        "ORD-1003 | Shipped\n"
        "ORD-1004 | Damaged In Transit\n"
        "ORD-1005 | Processing",
        language="text"
    )
    st.markdown("---")
    if st.button("🔄 Reset Form", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# Main Interface
st.title("🛡️ AI Customer Complaint Resolution Agent")
st.caption("Automated complaint analysis, policy checking, order lookup, response drafting, and direct email delivery.")

if not groq_api_key:
    st.error("⚠️ **Groq API Key Missing!** Please set `GROQ_API_KEY` in your `.env` file or Streamlit Secrets.")
    st.stop()

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    customer_name = st.text_input("Customer Name", value="John Doe")
with col2:
    customer_email = st.text_input("Customer Email", value="customer@example.com")
with col3:
    order_id_input = st.text_input("Order ID", value="ORD-1001", help="Enter sample Order ID like ORD-1001, ORD-1004, or leave empty.")

complaint_input = st.text_area(
    "Customer Complaint Text",
    value="My order is 10 days late. I contacted support twice without a response.",
    height=140
)

analyze_btn = st.button("🚀 Analyze & Resolve Complaint", type="primary", use_container_width=True)

if analyze_btn:
    if not complaint_input or len(complaint_input.strip()) < 5:
        st.warning("Please provide a complete customer complaint (minimum 5 characters).")
    else:
        with st.spinner("Analyzing complaint, querying policy database, and verifying order status..."):
            try:
                result: ComplaintAnalysisResult = process_complaint(
                    complaint_text=complaint_input,
                    order_id=order_id_input,
                    customer_name=customer_name,
                    api_key=groq_api_key
                )
                st.session_state["result"] = result
                st.success("Analysis and Ticket Generation Complete!")
            except Exception as e:
                st.error(f"Execution Error: {str(e)}")

# Results Display Section
if "result" in st.session_state:
    res: ComplaintAnalysisResult = st.session_state["result"]
    
    st.markdown("---")
    st.header("📊 Resolution Analysis & Actions")

    # Metric Row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Category", res.complaint_category)
    
    priority_colors = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"}
    m2.metric("Priority", f"{priority_colors.get(res.priority, '⚪')} {res.priority}")
    
    m3.metric("Decision", "🔴 Escalate" if res.escalation_required else "🟢 Resolve")
    m4.metric("Ticket ID", res.ticket_id)

    st.markdown("### 1. Complaint & Priority Analysis")
    st.info(f"**Summary:** {res.complaint_summary}\n\n**Priority Reason:** {res.priority_reason}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### 2. Verified Order Status")
        st.json({
            "Order ID": res.order_id,
            "Database Status": res.order_status
        })

    with col_b:
        st.markdown("### 3. Company Policy Lookup")
        st.json({
            "Policy Located": res.policy_found,
            "Policy Summary": res.policy_summary
        })

    st.markdown("### 4. Decision & Next Actions")
    st.warning(f"**Decision Reason:** {res.decision_reason}\n\n**Recommended Action:** {res.recommended_action}")

    st.markdown("### 5. Professional Customer Reply")
    edited_reply = st.text_area("Drafted Customer Communication", value=res.customer_reply, height=160)

    st.markdown("### 📧 Send Email to Customer")
    if st.button("📩 Send Response Email Now", use_container_width=True):
        with st.spinner("Sending email..."):
            email_res = send_customer_email(
                recipient_email=customer_email,
                subject=f"Update regarding Order {res.order_id} - Ticket {res.ticket_id}",
                message_body=edited_reply
            )
            if email_res["success"]:
                st.success(email_res["message"])
            else:
                st.error(email_res["message"])

    st.markdown("### 6. Generated Internal Support Ticket")
    ticket_dict = res.model_dump()
    st.json(ticket_dict)
    
    st.download_button(
        label="📥 Download Ticket JSON",
        data=json.dumps(ticket_dict, indent=2),
        file_name=f"ticket_{res.ticket_id}.json",
        mime="application/json"
    )