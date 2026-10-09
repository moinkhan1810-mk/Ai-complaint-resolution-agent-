import os
import pandas as pd
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from crewai import LLM
from dotenv import load_dotenv

load_dotenv()

# --- Initialize Groq LLM ---
llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    temperature=0.2
)
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
)

# --- Define Custom Tools ---

@tool("Policy Lookup Tool")
def policy_lookup_tool(query: str) -> str:
    """Useful to look up company policies regarding complaints, refunds, and escalations."""
    try:
        with open('data/company_policy.txt', 'r') as file:
            policy = file.read()
        return policy
    except Exception as e:
        return f"Error reading policy file: {e}"

@tool("Order Database Tool")
def order_database_tool(order_id: str) -> str:
    """Useful to look up the status of a specific order using the order ID."""
    try:
        df = pd.read_csv('data/orders.csv')
        # Convert order_id to int for matching if it's numeric
        try:
            order_id_int = int(order_id.strip())
            order_data = df[df['order_id'] == order_id_int]
        except ValueError:
            order_data = df[df['order_id'] == order_id]
            
        if order_data.empty:
            return f"Order ID {order_id} not found in database."
        
        # Return as a dictionary string
        return order_data.to_dict(orient='records')[0]
    except Exception as e:
        return f"Error querying database: {e}"

# --- Define the Agent ---

complaint_agent = Agent(
    role='Customer Complaint Resolution Specialist',
    goal='Analyze customer complaints, look up policies and order data, decide on a resolution, draft a reply, and prepare a support ticket.',
    backstory="You are an expert AI customer service agent. You handle frustrated customers with empathy. "
              "You strictly follow company policy. If a customer has contacted support twice without a response, "
              "you always escalate the issue to a Tier 2 manager.",
    verbose=True,
    allow_delegation=False,
    tools=[policy_lookup_tool, order_database_tool],
    llm=llm
)

# --- Define the Task ---
# We instruct the agent to output exactly what the slide requires: Category, Priority, Resolution, Reply, Ticket.

def create_complaint_task(user_request):
    return Task(
        description=f"""
        Analyze the following customer complaint:
        "{user_request}"
        
        Follow this exact workflow:
        1. Analyze the complaint to determine the category and urgency/priority.
        2. If an Order ID is mentioned, use the 'Order Database Tool' to look up its status and delay days.
        3. Use the 'Policy Lookup Tool' to find the relevant resolution rules based on the order status and previous contacts.
        4. Decide whether to resolve the issue yourself or escalate it based on the policy.
        5. Draft a professional, empathetic reply to the customer based on the policy.
        6. Prepare an internal support ticket summary.
        
        Your final output MUST be formatted strictly as a JSON object with the following keys:
        "category": "The category of the complaint (e.g., Shipping Delay, Billing, etc.)",
        "priority": "The priority level (e.g., High, Medium, Low)",
        "proposed_resolution": "A summary of what is being offered or done (e.g., Escalated to Tier 2, 15% refund)",
        "reply": "The exact text of the email reply to send to the customer.",
        "ticket": "The internal notes for the support ticket."
        """,
        expected_output="A strict JSON object containing category, priority, proposed_resolution, reply, and ticket.",
        agent=complaint_agent
    )

# --- Main Execution Function ---

def run_complaint_agent(user_request):
    task = create_complaint_task(user_request)
    
    crew = Crew(
        agents=[complaint_agent],
        tasks=[task],
        process=Process.sequential
    )
    
    result = crew.kickoff()
    return result
