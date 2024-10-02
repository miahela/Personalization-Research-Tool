from pydantic import BaseModel, Field
from typing import List, Optional


class CompanyData(BaseModel):
    name: str
    website: Optional[str] = None
    about_links: List[dict] = Field(default_factory=list)
    case_study_links: List[dict] = Field(default_factory=list)


class ContactData(BaseModel):
    spreadsheet_id: str
    row_number: int
    colored_cells: List[str] = Field(default_factory=list)
    contact_first_name: str
    contact_last_name: str
    contact_job_title: str
    contact_company_name: str
    hook_name: str
    messenger_campaign_instance: Optional[str] = None
    parsed_name: str
    company: CompanyData
    contact_profile_link: str
    linkedin_username: str
    profile_picture: Optional[str] = None
    bio: Optional[str] = None
    headline: Optional[str] = None
    industry: Optional[str] = None
    banner_picture: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    experiences: List[dict] = Field(default_factory=list)
    volunteer_work: List[dict] = Field(default_factory=list)
    interviews_and_podcasts: List[dict] = Field(default_factory=list)
