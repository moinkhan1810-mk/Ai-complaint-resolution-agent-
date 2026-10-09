import os
import json
import datetime
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
from crewai.tools import tool

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TICKETS_DIR = os.path.join(BASE_DIR, "tickets")

@tool("Company Policy Lookup Tool")
def policy_lookup_tool(category_or_keyword: str) -> str:
    """
    Searches company policies in JSON by category or keyword.
    Args:
        category_or_keyword: Keyword or category name (e.g., 'late', 'damaged', 'refund', 'missing', 'cancellation', 'payment').
    """
    policy_path = os.path.join(DATA_DIR, "company_policies.json")
    if not os.path.exists(policy_path):
        return json.dumps({"error": "Policy database file not found."})

    try:
        with open(policy_path, "r", encoding="utf-8") as f:
            policies = json.load(f)

        query = str(category_or_keyword).lower()
        matched = []

        for key, details in policies.items():
            cat = details.get("category", "").lower()
            pol = details.get("policy", "").lower()
            if query in key.lower() or query in cat or any(term in pol for term in query.split()):
                matched.append(details)

        if matched:
            return json.dumps({"status": "success", "policies_found": matched}, indent=2)
        else:
            return json.dumps({
                "status": "not_found",
                "message": f"No specific company policy matching '{category_or_keyword}' was found."
            })
    except Exception as e:
        return json.dumps({"error": f"Error searching policy database: {str(e)}"})

@tool("Order Status Lookup Tool")
def order_lookup_tool(order_id: str) -> str:
    """
    Searches the orders database for an order by Order ID.
    Args:
        order_id: The order identifier (e.g., 'ORD-1001').
    """
    orders_path = os.path.join(DATA_DIR, "orders.csv")
    if not os.path.exists(orders_path):
        return json.dumps({"error": "Orders database file not found."})

    if not order_id or str(order_id).strip().lower() in ["none", "null", "not provided", ""]:
        return json.dumps({"status": "missing_id", "message": "No valid Order ID was provided."})

    clean_id = str(order_id).strip().upper()

    try:
        df = pd.read_csv(orders_path)
        df["order_id"] = df["order_id"].astype(str).str.strip().str.upper()
        record = df[df["order_id"] == clean_id]

        if not record.empty:
            order_data = record.iloc[0].to_dict()
            return json.dumps({"status": "found", "order_details": order_data}, indent=2)
        else:
            return json.dumps({
                "status": "not_found",
                "message": f"Order ID '{clean_id}' was not found in database records."
            })
    except Exception as e:
        return json.dumps({"error": f"Error reading order database: {str(e)}"})

@tool("Support Ticket Generator Tool")
def generate_ticket_tool(ticket_data_json: str) -> str:
    """
    Generates and persists an internal customer support ticket locally.
    Args:
        ticket_data_json: JSON string or dictionary containing ticket details.
    """
    os.makedirs(TICKETS_DIR, exist_ok=True)
    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"

    try:
        data = json.loads(ticket_data_json) if isinstance(ticket_data_json, str) else ticket_data_json
    except Exception:
        data = {"raw_summary": str(ticket_data_json)}

    data["ticket_id"] = ticket_id
    data["created_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    data["saved_locally"] = True

    filepath = os.path.join(TICKETS_DIR, f"{ticket_id}.json")
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return json.dumps({
            "status": "success",
            "ticket_id": ticket_id,
            "file_path": filepath,
            "message": "Internal support ticket generated and stored locally."
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "ticket_id": ticket_id,
            "message": f"Failed to persist ticket record: {str(e)}"
        })

def send_customer_email(recipient_email: str, subject: str, message_body: str) -> dict:
    """
    Sends an email directly to the customer using SMTP settings from environment variables.
    """
    sender_email = os.environ.get("SENDER_EMAIL")
    sender_password = os.environ.get("SENDER_APP_PASSWORD")

    if not sender_email or not sender_password:
        return {
            "success": False,
            "message": "Missing email credentials. Please set SENDER_EMAIL and SENDER_APP_PASSWORD in your .env file."
        }

    if not recipient_email or "@" not in recipient_email:
        return {
            "success": False,
            "message": "Invalid recipient email address."
        }

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message_body, 'plain'))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        return {
            "success": True,
            "message": f"Email successfully sent to {recipient_email}!"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Email sending failed: {str(e)}"
        }