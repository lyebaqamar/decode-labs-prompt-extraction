from enum import Enum
from typing import Optional, Set
from pydantic import BaseModel, ConfigDict, Field, field_validator

class ComplaintType(str, Enum):
    BILLING = "Billing"
    DELIVERY = "Delivery"
    PRODUCT_QUALITY = "Product Quality"
    REFUND = "Refund"
    TECHNICAL_SUPPORT = "Technical Support"
    OTHER = "Other"

class SupportTicket(BaseModel):
    """
    This is my primary data model contract representing the structured schema 
    extracted from raw customer support emails. I have implemented strict 
    data-type handling and bounds validation to ensure downstream safety.
    """
    customer_name: Optional[str] = Field(
        default=None, 
        description="The full name of the customer making the complaint or inquiry."
    )
    order_number: Optional[str] = Field(
        default=None, 
        description="The alphanumeric order identifier."
    )
    complaint_type: ComplaintType = Field(
        description="The categorized type of the support complaint."
    )
    severity_level: int = Field(
        description="An integer from 1 (lowest priority) to 5 (highest priority/severe)."
    )
    contact_phone: Optional[str] = Field(
        default=None, 
        description="The contact telephone number."
    )

    # I forbid extra keys to prevent the LLM from hallucinating additional fields
    model_config = ConfigDict(extra="forbid")

    @field_validator("customer_name", "order_number", "contact_phone", mode="before")
    @classmethod
    def empty_string_to_null(cls, value):
        """
        I handle blank/whitespace strings explicitly here, normalizing them 
        to Python None (JSON null) to guarantee structural alignment.
        """
        if isinstance(value, str):
            stripped = value.strip()
            return None if stripped == "" else stripped
        return value

    @field_validator("severity_level")
    @classmethod
    def validate_severity_range(cls, value: int) -> int:
        """
        I enforce that the severity rating stays strictly within the 1-5 bound.
        """
        if not (1 <= value <= 5):
            raise ValueError("Severity level must be an integer between 1 and 5.")
        return value

# I defined this set to manually verify raw dictionary structure before parsing with Pydantic
REQUIRED_KEYS: Set[str] = {
    "customer_name",
    "order_number",
    "complaint_type",
    "severity_level",
    "contact_phone"
}