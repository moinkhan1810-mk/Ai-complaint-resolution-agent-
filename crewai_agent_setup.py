import os
import json
import re
from crewai import Agent, Task, Crew, LLM
from models import ComplaintAnalysisResult
from tools import policy_lookup_tool, order_lookup_tool, generate_ticket_tool

def build_resolution_crew(api_key: str = None):
    groq_key = api_key or os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise ValueError("GROQ_API_KEY is not configured. Set it in .env or Streamlit Secrets.")

    # Using the stable supported Groq model
    llm = LLM(
        model="groq/llama-3.3-70b-versatile",
        api_key=groq_key,
        temperature=0.1
    )

    resolution_agent = Agent(
        role="Senior Customer Support Resolution Specialist",
        goal="Analyze customer complaints, verify facts via tools, decide on resolution or escalation, draft empathetic replies, and generate support tickets.",
        backstory=(
            "You are an empathetic, precise customer support specialist. You rely strictly on "
            "data returned by local tools, never make up delivery dates or refunds, and follow "
            "company policy accurately."
        ),
        tools=[policy_lookup_tool, order_lookup_tool, generate_ticket_tool],
        llm=llm,
        verbose=True
    )

    resolution_task = Task(
        description=(
            "Execute the following 5 steps to process the customer complaint:\n\n"
            "STEP 1: Analyze Complaint & Urgency\n"
            "- Extract complaint category, priority (Low, Medium, High, Critical), priority reason, and key details.\n\n"
            "STEP 2: Look Up Policy & Order Status\n"
            "- Call 'Order Status Lookup Tool' for Order ID '{order_id}'.\n"
            "- Call 'Company Policy Lookup Tool' for the identified complaint category.\n"
            "- ONLY rely on actual returned data. If order/policy is not found, record it explicitly.\n\n"
            "STEP 3: Decide Resolve vs Escalate\n"
            "- Decide 'Resolve' or 'Escalate' based on verified policy and order facts.\n"
            "- Explain the decision clearly.\n\n"
            "STEP 4: Draft Professional Customer Reply\n"
            "- Write an empathetic, polite reply acknowledging the customer issue using verified details.\n\n"
            "STEP 5: Prepare Support Ticket\n"
            "- Call 'Support Ticket Generator Tool' to create a ticket record.\n\n"
            "Customer Input:\n"
            "- Customer Name: {customer_name}\n"
            "- Order ID: {order_id}\n"
            "- Complaint: {complaint_text}"
        ),
        expected_output="A structured JSON object matching ComplaintAnalysisResult schema.",
        output_pydantic=ComplaintAnalysisResult,
        agent=resolution_agent
    )

    return Crew(agents=[resolution_agent], tasks=[resolution_task], verbose=True)

def process_complaint(complaint_text: str, order_id: str = None, customer_name: str = "Valued Customer", api_key: str = None) -> ComplaintAnalysisResult:
    crew = build_resolution_crew(api_key=api_key)
    result = crew.kickoff(inputs={
        "complaint_text": complaint_text,
        "order_id": order_id if order_id and order_id.strip() else "None",
        "customer_name": customer_name if customer_name and customer_name.strip() else "Valued Customer"
    })

    if hasattr(result, "pydantic") and result.pydantic:
        return result.pydantic

    raw_output = str(result.raw if hasattr(result, "raw") else result)
    json_match = re.search(r"\{.*\}", raw_output, re.DOTALL)
    if json_match:
        data = json.loads(json_match.group(0))
        return ComplaintAnalysisResult(**data)
    
    raise ValueError("Failed to parse structured output from model response.")