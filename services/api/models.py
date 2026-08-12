from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from sqlmodel import Field as SQLModelField
from sqlmodel import SQLModel

SUPPLIER_CATEGORIES: tuple[str, ...] = (
    "medical_supplies",
    "laboratory_services",
    "pharmaceutical",
    "clinical_software",
    "it_infrastructure",
    "hr_and_payroll_software",
    "cleaning_and_facilities",
    "patient_communication",
    "billing_and_coding_software",
    "training_platforms",
)

SUPPLIER_STATUSES: tuple[str, ...] = ("active", "suspended")

INITIAL_SUPPLIERS: tuple[dict[str, object], ...] = (
    {
        "name": "McKesson Medical Supplies",
        "country": "USA",
        "categories": ["medical_supplies"],
        "monthly_rate": 4200.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": "BAA",
        "contract_renewal_date": "2025-06-30",
        "contact_email": "accounts@mckesson.com",
        "notes": "Primary clinical supplies provider for the 9 USA clinics.",
    },
    {
        "name": "NHS Supply Chain",
        "country": "UK",
        "categories": ["medical_supplies"],
        "monthly_rate": 2800.0,
        "currency": "GBP",
        "status": "active",
        "compliance_agreement": "DPA",
        "contact_email": "enquiries@supplychain.nhs.uk",
    },
    {
        "name": "Quest Diagnostics",
        "country": "USA",
        "categories": ["laboratory_services"],
        "monthly_rate": 3100.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": "BAA",
        "contract_renewal_date": "2025-12-15",
        "contact_email": "business@questdiagnostics.com",
        "notes": "Laboratory processing for Texas and Florida clinics.",
    },
    {
        "name": "Synnovis UK",
        "country": "UK",
        "categories": ["laboratory_services"],
        "monthly_rate": 1950.0,
        "currency": "GBP",
        "status": "active",
        "compliance_agreement": "DPA",
        "contact_email": "contracts@synnovis.co.uk",
    },
    {
        "name": "Epic Systems",
        "country": "USA",
        "categories": ["clinical_software"],
        "monthly_rate": 8500.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": "BAA",
        "contract_renewal_date": "2026-01-01",
        "contact_email": "enterprise@epic.com",
        "notes": "Primary EHR for USA clinics. Long-term contract.",
    },
    {
        "name": "EMIS Health",
        "country": "UK",
        "categories": ["clinical_software"],
        "monthly_rate": 3400.0,
        "currency": "GBP",
        "status": "active",
        "compliance_agreement": "DPA",
        "contract_renewal_date": "2025-09-01",
        "contact_email": "accounts@emishealth.com",
        "notes": "EHR for London and Manchester clinics.",
    },
    {
        "name": "Availity",
        "country": "USA",
        "categories": ["billing_and_coding_software"],
        "monthly_rate": 1200.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": "BAA",
        "contact_email": "enterprise@availity.com",
        "notes": "Eligibility verification and claims submission platform.",
    },
    {
        "name": "Twilio",
        "country": "USA",
        "categories": ["patient_communication"],
        "monthly_rate": 680.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": "BAA",
        "contract_renewal_date": "2025-10-31",
        "contact_email": "healthcare@twilio.com",
        "notes": "Automated SMS and email for appointment reminders.",
    },
    {
        "name": "AWS Healthcare",
        "country": "USA",
        "categories": ["it_infrastructure"],
        "monthly_rate": 5600.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": "BAA",
        "contact_email": "aws-health@amazon.com",
        "notes": "Primary cloud infrastructure. BAA signed and audited annually.",
    },
    {
        "name": "Microsoft Azure UK",
        "country": "UK",
        "categories": ["it_infrastructure"],
        "monthly_rate": 2100.0,
        "currency": "GBP",
        "status": "active",
        "compliance_agreement": "DPA",
        "contact_email": "enterprise@microsoft.com",
    },
    {
        "name": "Workday",
        "country": "USA",
        "categories": ["hr_and_payroll_software"],
        "monthly_rate": 2400.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": None,
        "contract_renewal_date": "2025-08-15",
        "contact_email": "enterprise@workday.com",
        "notes": "HRIS for the entire USA workforce. Does not handle PHI.",
    },
    {
        "name": "Sage Payroll UK",
        "country": "UK",
        "categories": ["hr_and_payroll_software"],
        "monthly_rate": 890.0,
        "currency": "GBP",
        "status": "active",
        "compliance_agreement": "DPA",
        "contact_email": "business@sage.co.uk",
    },
    {
        "name": "ServiceMaster Clean",
        "country": "USA",
        "categories": ["cleaning_and_facilities"],
        "monthly_rate": 3800.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": None,
        "contact_email": "healthcare@servicemaster.com",
        "notes": "Clinical cleaning for the 9 USA locations.",
    },
    {
        "name": "Healthstream LMS",
        "country": "USA",
        "categories": ["training_platforms"],
        "monthly_rate": 1100.0,
        "currency": "USD",
        "status": "suspended",
        "compliance_agreement": "BAA",
        "contact_email": "enterprise@healthstream.com",
        "notes": "Suspended. Diane is evaluating replacing it with an in-house solution.",
    },
    {
        "name": "Nuffield Health Supplies",
        "country": "UK",
        "categories": ["medical_supplies", "cleaning_and_facilities"],
        "monthly_rate": 1650.0,
        "currency": "GBP",
        "status": "active",
        "compliance_agreement": "DPA",
        "contact_email": "procurement@nuffieldhealth.com",
    },
)


class SupplierStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class SupplierCategory(str, Enum):
    MEDICAL_SUPPLIES = "medical_supplies"
    LABORATORY_SERVICES = "laboratory_services"
    PHARMACEUTICAL = "pharmaceutical"
    CLINICAL_SOFTWARE = "clinical_software"
    IT_INFRASTRUCTURE = "it_infrastructure"
    HR_AND_PAYROLL_SOFTWARE = "hr_and_payroll_software"
    CLEANING_AND_FACILITIES = "cleaning_and_facilities"
    PATIENT_COMMUNICATION = "patient_communication"
    BILLING_AND_CODING_SOFTWARE = "billing_and_coding_software"
    TRAINING_PLATFORMS = "training_platforms"


class ComplianceAgreement(str, Enum):
    BAA = "BAA"
    DPA = "DPA"
    BOTH = "both"


SupplierCountry = Literal["USA", "UK"]
SupplierCurrency = Literal["USD", "GBP"]


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    country: SupplierCountry
    categories: list[SupplierCategory] = Field(min_length=1)
    monthly_rate: float = Field(gt=0)
    currency: SupplierCurrency
    status: SupplierStatus
    compliance_agreement: ComplianceAgreement | None = None
    contract_renewal_date: str | None = None
    contact_email: EmailStr | None = None
    notes: str | None = None

    @field_validator("contract_renewal_date")
    @classmethod
    def validate_contract_renewal_date(cls, value: str | None) -> str | None:
        if value is not None:
            date.fromisoformat(value)
        return value

    @model_validator(mode="after")
    def validate_currency_for_country(self) -> "SupplierCreate":
        expected_currency = "USD" if self.country == "USA" else "GBP"
        if self.currency != expected_currency:
            raise ValueError(f"{self.country} suppliers must use {expected_currency}")
        return self


class SupplierResponse(SupplierCreate):
    id: int
    updated_at: datetime


class SupplierRateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monthly_rate: float = Field(gt=0)


class SupplierStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: SupplierStatus


class Product(SQLModel, table=True):
    """Supabase product identity; stock is derived from order history."""

    __tablename__ = "products"

    id: int | None = SQLModelField(default=None, primary_key=True)
    name: str = SQLModelField(index=True, max_length=200)
    sku: str = SQLModelField(index=True, unique=True, max_length=64)


class InboundOrder(SQLModel, table=True):
    """Immutable order fact that adds quantity to a product's derived stock."""

    __tablename__ = "inbound_orders"

    id: int | None = SQLModelField(default=None, primary_key=True)
    product_id: int = SQLModelField(foreign_key="products.id", index=True)
    quantity: int = SQLModelField(gt=0)
    created_at: datetime = SQLModelField(default_factory=lambda: datetime.now(timezone.utc))
    user_uuid: str = SQLModelField(index=True, max_length=64)


class OutboundOrder(SQLModel, table=True):
    """Immutable order fact that subtracts quantity from derived stock."""

    __tablename__ = "outbound_orders"

    id: int | None = SQLModelField(default=None, primary_key=True)
    product_id: int = SQLModelField(foreign_key="products.id", index=True)
    quantity: int = SQLModelField(gt=0)
    created_at: datetime = SQLModelField(default_factory=lambda: datetime.now(timezone.utc))
    user_uuid: str = SQLModelField(index=True, max_length=64)
