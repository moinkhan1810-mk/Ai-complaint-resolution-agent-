from pydantic import BaseModel, Field
from typing import Optional

class ComplaintInput(BaseModel):
    complaint_text: str = Field(..., min_length=5, description="Customer complaint text")
    order_id: Optional[str] = Field(default=None, description="Optional customer Order ID")
    customer_name: Optional[str] = Field(default="Valued Customer", description="Customer reference name")

class ComplaintAnalysisResult(BaseModel):
    complaint_category: str = Field(..., description="Category: Late Delivery, Damaged Product, Refunds, Missing Item, Cancellation, Payment Issue, or Other")
    priority: str = Field(..., description="Priority level: Low, Medium, High, or Critical")
    priority_reason: str = Field(..., description="Justification for assigned priority")
    complaint_summary: str = Field(..., description="Concise summary of customer issue")
    order_id: str = Field(default="Not Provided", description="Verified Order ID or 'Not Provided' / 'Not Found'")
    order_status: str = Field(..., description="Verified status from database or 'Not Found' / 'Unverified'")
    policy_found: bool = Field(..., description="True if an applicable policy was retrieved")
    policy_summary: str = Field(..., description="Summary of relevant policy retrieved")
    decision: str = Field(..., description="Action decision: Resolve or Escalate")
    decision_reason: str = Field(..., description="Reasoning for decision")
    recommended_action: str = Field(..., description="Internal next action for support team")
    customer_reply: str = Field(..., description="Drafted professional customer-facing response")
    ticket_id: str = Field(..., description="Unique ticket ID generated for this record")
    escalation_required: bool = Field(..., description="True if human intervention is necessary")
    escalation_reason: Optional[str] = Field(default=None, description="Reason for escalation if required")
