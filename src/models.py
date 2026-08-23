from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

class Provenance(BaseModel):
    field: str
    page_start: int
    page_end: int
    evidence: str = ""

class Reservation(BaseModel):
    ur: Optional[int] = None
    ews: Optional[int] = None
    obc: Optional[int] = None
    sc: Optional[int] = None
    st: Optional[int] = None
    pwbd: Optional[int] = None
    ex_servicemen: Optional[int] = None
    other: str = ""

class Recruitment(BaseModel):
    advertisement_no: str
    vacancy_no: str = ""
    post_title: str = ""
    ministry: str = ""
    department: str = ""
    organisation: str = ""
    total_vacancies: Optional[int] = None
    reservation: Reservation = Field(default_factory=Reservation)

    classification: str = ""
    service_status: str = ""
    pay_level: str = ""
    pay_scale: str = ""
    salary: str = ""
    age_limit: str = ""
    age_relaxation: str = ""
    essential_qualification: str = ""
    desirable_qualification: str = ""
    essential_experience: str = ""
    desirable_experience: str = ""
    duties: str = ""
    headquarters: str = ""
    posting: str = ""
    probation: str = ""
    service_liability: str = ""
    pwbd_suitability: str = ""
    selection_process: str = ""
    application_start: str = ""
    application_end: str = ""
    application_fee: str = ""
    application_mode: str = "Online"
    application_url: str = "https://upsconline.nic.in/ora/"
    notification_url: str = ""
    important_instructions: str = ""
    contact: str = ""

    pages_start: Optional[int] = None
    pages_end: Optional[int] = None
    confidence: float = 0.0
    provenance: list[Provenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class Page(BaseModel):
    number: int
    text: str
