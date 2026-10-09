"""Plain-Python helpers: policy lookup, order lookup and ticket creation.

This file has no CrewAI or Streamlit imports, so it is easy to test on its own.
agent.py wraps the lookup functions as CrewAI tools; the ticket is created by
Python code AFTER the agent's answer has been validated (never by the LLM itself).
"""
import csv
import json
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TICKETS_DIR = BASE_DIR / "tickets"
POLICY_FILE = DATA_DIR / "company_policies.json"
ORDER_FILE = DATA_DIR / "orders.csv"

# Which policy applies to which complaint category (used to double-check the agent).
CATEGORY_TO_POLICY_ID = {
    "Delayed Order": "late_delivery",
    "Refund Request": "refunds_returns",
    "Damaged Product": "damaged_products",
    "Missing Item": "missing_items",
    "Cancellation": "cancellations",
    "Payment Issue": "payment_problems",
}

ORDER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-]{1,20}$")
_ORDER_IN_TEXT = re.compile(r"\bORD-?\s?(\d{3,})\b", re.IGNORECASE)


class DataError(Exception):
    """A data file is missing or unreadable."""


class TicketError(Exception):
    """The ticket could not be created because required information is missing."""


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------
def load_policies() -> list:
    try:
        with open(POLICY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise DataError("The company policy file could not be read.") from exc


def _public_policy(policy: dict) -> dict:
    return {
        "id": policy["id"],
        "category": policy["category"],
        "title": policy["title"],
        "policy": policy["policy"],
    }


def search_policies(query: str, limit: int = 2) -> list:
    """Keyword search. Returns [] when nothing matches (we never invent a policy)."""
    text = (query or "").lower()
    scored = []
    for policy in load_policies():
        score = sum(1 for kw in policy.get("keywords", []) if kw.lower() in text)
        if score:
            scored.append((score, policy))
    scored.sort(key=lambda item: -item[0])
    return [_public_policy(p) for _, p in scored[:limit]]


def policies_for_category(category: str) -> list:
    policy_id = CATEGORY_TO_POLICY_ID.get(category)
    if not policy_id:
        return []
    return [_public_policy(p) for p in load_policies() if p["id"] == policy_id]


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
def normalize_order_id(raw: str) -> str:
    value = (raw or "").strip().upper().replace(" ", "")
    if value.isdigit():
        return "ORD-" + value
    match = re.fullmatch(r"ORD(\d+)", value)
    if match:
        return "ORD-" + match.group(1)
    return value


def extract_order_id(text: str):
    """Find something like ORD-1001 inside the complaint text."""
    match = _ORDER_IN_TEXT.search(text or "")
    return f"ORD-{match.group(1)}" if match else None


def _parse_date(value):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _enrich(row: dict) -> dict:
    """Clean empty values and add day counts calculated from today's date."""
    row = {k: (v.strip() if isinstance(v, str) and v.strip() else None) for k, v in row.items()}
    today = date.today()
    expected = _parse_date(row.get("expected_delivery"))
    delivered = _parse_date(row.get("delivered_date"))
    row["today"] = today.isoformat()
    row["days_past_expected_delivery"] = None
    row["days_since_delivery"] = None
    if row.get("status") not in ("Delivered", "Cancelled") and expected and expected < today:
        row["days_past_expected_delivery"] = (today - expected).days
    if delivered:
        row["days_since_delivery"] = (today - delivered).days
    return row


def find_order(order_id: str):
    """Return the order record (dict) or None if it does not exist."""
    wanted = normalize_order_id(order_id)
    if not wanted:
        return None
    try:
        with open(ORDER_FILE, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if (row.get("order_id") or "").strip().upper() == wanted:
                    return _enrich(row)
    except OSError as exc:
        raise DataError("The order data file could not be read.") from exc
    return None


# ---------------------------------------------------------------------------
# Tickets (prepared and saved LOCALLY only - nothing is sent to a real system)
# ---------------------------------------------------------------------------
REQUIRED_TICKET_FIELDS = [
    "complaint_category",
    "priority",
    "complaint_summary",
    "decision",
    "recommended_action",
    "customer_reply",
]


def create_ticket(result: dict, order_record=None, policy_text: str = ""):
    """Validate, build and save a ticket. Returns (ticket_dict, saved_bool, message)."""
    missing = [key for key in REQUIRED_TICKET_FIELDS if not result.get(key)]
    if missing:
        raise TicketError("Cannot create ticket, missing: " + ", ".join(missing))

    now = datetime.now(timezone.utc)
    ticket_id = f"TCK-{now:%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    escalate = result.get("decision") == "Escalate"
    ticket = {
        "ticket_id": ticket_id,
        "order_id": result.get("order_id"),
        "complaint_category": result["complaint_category"],
        "complaint_summary": result["complaint_summary"],
        "priority": result["priority"],
        "relevant_policy": policy_text or result.get("policy_summary") or "No matching policy found",
        "verified_order_status": order_record["status"] if order_record else "Not verified",
        "recommended_resolution": result["recommended_action"],
        "escalation_status": "Escalated - needs human review" if escalate else "Not escalated",
        "escalation_reason": result.get("escalation_reason"),
        "suggested_action_for_support_team": result["recommended_action"],
        "draft_customer_response": result["customer_reply"],
        "created_at": now.isoformat(timespec="seconds"),
        "submission_status": "Prepared locally. NOT submitted to any external support system.",
    }

    try:
        TICKETS_DIR.mkdir(exist_ok=True)
        with open(TICKETS_DIR / f"{ticket_id}.json", "x", encoding="utf-8") as f:
            json.dump(ticket, f, indent=2, ensure_ascii=False)
        return ticket, True, f"Saved to tickets/{ticket_id}.json"
    except OSError:
        return ticket, False, "The ticket could not be saved (the filesystem may be read-only). You can still download it."
