from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum 
from datetime import date

class DocumentType(str, Enum):
    INVOICE = "invoice"
    CONTRACT = "contract"
    RECEIPT = "receipt"
    LEGAL = "legal"
    FINANCIAL = "financial"
    UNKNOWN = "unknown"

class ProcessingStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    OCR_REQUIRED = "ocr_required"

class FlagSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Flag(BaseModel):
    """A single issue or warning flagged in the document."""
    issue: str = Field(description="Clear description of the issue found")
    severity: FlagSeverity = Field(description="How serious this issue is")
    location: Optional[str] = Field(
        default=None,
        description="Where in the document this was found (e.g., 'Section 3', 'Line 12')"
    )
    recommendation: str = Field(description="What should be done about this issue")

class InvoiceData(BaseModel):
    """Structured data extracted from an invoice."""
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    client_name: Optional[str] = None
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = Field(default="USD")
    line_items: Optional[List[dict]] = Field(default_factory=list)
    payment_terms: Optional[str] = None
    bank_details: Optional[str] = None

class ContractData(BaseModel):
    """Structured data extracted from a contract."""
    contract_type: Optional[str] = None
    parties: Optional[List[str]] = Field(default_factory=list)
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    jurisdiction: Optional[str] = None
    governing_law: Optional[str] = None
    key_obligations: Optional[List[str]] = Field(default_factory=list)
    payment_terms: Optional[str] = None
    termination_causes: Optional[list[str]] = Field(default_factory=list)
    auto_renewal: Optional[bool] = None
    penalty_causes: Optional[List[str]] = Field(default_factory=list)
    confidentiality_clause: Optional[bool] = None
    none_compete_clause: Optional[bool] = None

class DocumentExtraction(BaseModel):
    """
    The top-level model. Every processed document returns on of these.
    This is what gets saved, displayed, and validated.
    """
    document_type: DocumentType
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="How confidenct the model is in its extraction (0.0 to 1.0)"
    )
    summary: str = Field(description="2-4 sentence plain English summary of the document")
    flags: List[Flag] = Field(
        default_factory=list,
        description="List of issues, risks, or anomolies found"
    )
    invoice_data: Optional[InvoiceData] = None
    contract_data: Optional[ContractData] = None
    raw_key_fields: dict = Field(
        default_factory=dict,
        description="Any other important fields not covered by types models"
    )
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    extraction_method: str = Field(
        default="text",
        description="'text' for direct extraction, 'ocr' for scanned documents"
    )

    @field_validator('confidence_score')
    @classmethod
    def round_confidence(cls, v):
        return round(v, 2)