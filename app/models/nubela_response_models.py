from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

from app.models import PqKeywords


class Date(BaseModel):
    day: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None


class Experience(BaseModel):
    starts_at: Optional[Date] = None
    ends_at: Optional[Date] = None
    company: Optional[str] = None
    company_linkedin_profile_url: Optional[str] = None
    company_facebook_profile_url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    logo_url: Optional[str] = None

    @property
    def is_current(self) -> bool:
        return self.ends_at is None

    @property
    def duration(self) -> timedelta:
        start_date = self.get_start_date()
        if start_date is None:
            return timedelta(0)

        end_date = self.get_end_date()
        if end_date is None:
            return datetime.now() - start_date

        return end_date - start_date

    def duration_str(self) -> str:
        start_date = self.get_start_date()
        if start_date is None:
            return "Unknown duration"
        days = self.duration.days
        years, remaining_days = divmod(days, 365)
        months = remaining_days // 30
        return f"{years} years, {months} months"

    def matches_keywords(self, keywords: 'PqKeywords') -> bool:
        if not self.title:
            return False

        title_lower = self.title.lower()
        return (
                (any(title.lower() in title_lower for title in keywords.titles) or
                 any(seniority.lower() in title_lower for seniority in keywords.seniority)) and
                not any(keyword.lower() in title_lower for keyword in keywords.negative_keywords)
        )

    def get_start_date(self) -> Optional[datetime]:
        if self.starts_at and self.starts_at.year:
            return datetime(
                self.starts_at.year,
                self.starts_at.month or 1,
                self.starts_at.day or 1
            )
        return None

    def get_end_date(self) -> Optional[datetime]:
        if self.ends_at and self.ends_at.year:
            return datetime(
                self.ends_at.year,
                self.ends_at.month or 1,
                self.ends_at.day or 1
            )
        return None

    def __str__(self):
        return f"{self.title} at {self.company} ({self.duration_str()})"


class Education(BaseModel):
    starts_at: Optional[Date] = None
    ends_at: Optional[Date] = None
    field_of_study: Optional[str] = None
    degree_name: Optional[str] = None
    school: Optional[str] = None
    school_linkedin_profile_url: Optional[str] = None
    school_facebook_profile_url: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    grade: Optional[str] = None
    activities_and_societies: Optional[str] = None


class Language(BaseModel):
    name: Optional[str] = None
    proficiency: Optional[str] = None


class AccomplishmentOrg(BaseModel):
    starts_at: Optional[Date] = None
    ends_at: Optional[Date] = None
    org_name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class Publication(BaseModel):
    name: Optional[str] = None
    publisher: Optional[str] = None
    published_on: Optional[Date] = None
    description: Optional[str] = None
    url: Optional[str] = None


class HonourAward(BaseModel):
    title: Optional[str] = None
    issuer: Optional[str] = None
    issued_on: Optional[Date] = None
    description: Optional[str] = None


class Patent(BaseModel):
    title: Optional[str] = None
    issuer: Optional[str] = None
    issued_on: Optional[Date] = None
    description: Optional[str] = None
    application_number: Optional[str] = None
    patent_number: Optional[str] = None
    url: Optional[str] = None


class Course(BaseModel):
    name: Optional[str] = None
    number: Optional[str] = None


class Project(BaseModel):
    starts_at: Optional[Date] = None
    ends_at: Optional[Date] = None
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None


class TestScore(BaseModel):
    name: Optional[str] = None
    score: Optional[str] = None
    date_on: Optional[Date] = None
    description: Optional[str] = None


class VolunteeringExperience(BaseModel):
    starts_at: Optional[Date] = None
    ends_at: Optional[Date] = None
    title: Optional[str] = None
    cause: Optional[str] = None
    company: Optional[str] = None
    company_linkedin_profile_url: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None


class Certification(BaseModel):
    starts_at: Optional[Date] = None
    ends_at: Optional[Date] = None
    name: Optional[str] = None
    license_number: Optional[str] = None
    display_source: Optional[str] = None
    authority: Optional[str] = None
    url: Optional[str] = None


class PeopleAlsoViewed(BaseModel):
    link: Optional[str] = None
    name: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None


class Activity(BaseModel):
    title: Optional[str] = None
    link: Optional[str] = None
    activity_status: Optional[str] = None


class SimilarProfile(BaseModel):
    name: Optional[str] = None
    link: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None


class Article(BaseModel):
    title: Optional[str] = None
    link: Optional[str] = None
    published_date: Optional[Date] = None
    author: Optional[str] = None
    image_url: Optional[str] = None


class PersonGroup(BaseModel):
    profile_pic_url: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None


class InferredSalary(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None


class PersonExtra(BaseModel):
    github_profile_id: Optional[str] = None
    facebook_profile_id: Optional[str] = None
    twitter_profile_id: Optional[str] = None
    website: Optional[str] = None


class NubelaResponse(BaseModel):
    public_identifier: Optional[str] = None
    profile_pic_url: Optional[str] = None
    background_cover_image_url: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    follower_count: Optional[int] = None
    occupation: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    country: Optional[str] = None
    country_full_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    experiences: Optional[List[Experience]] = None
    education: Optional[List[Education]] = None
    languages: Optional[List[str]] = None
    languages_and_proficiencies: Optional[List[Language]] = None
    accomplishment_organisations: Optional[List[AccomplishmentOrg]] = None
    accomplishment_publications: Optional[List[Publication]] = None
    accomplishment_honors_awards: Optional[List[HonourAward]] = None
    accomplishment_patents: Optional[List[Patent]] = None
    accomplishment_courses: Optional[List[Course]] = None
    accomplishment_projects: Optional[List[Project]] = None
    accomplishment_test_scores: Optional[List[TestScore]] = None
    volunteer_work: Optional[List[VolunteeringExperience]] = None
    certifications: Optional[List[Certification]] = None
    connections: Optional[int] = None
    people_also_viewed: Optional[List[PeopleAlsoViewed]] = None
    recommendations: Optional[List[str]] = None
    activities: Optional[List[Activity]] = None
    similarly_named_profiles: Optional[List[SimilarProfile]] = None
    articles: Optional[List[Article]] = None
    groups: Optional[List[PersonGroup]] = None
    skills: Optional[List[str]] = None
    inferred_salary: Optional[InferredSalary] = None
    gender: Optional[str] = None
    birth_date: Optional[Date] = None
    industry: Optional[str] = None
    extra: Optional[PersonExtra] = None
    interests: Optional[List[str]] = None
    personal_emails: Optional[List[str]] = None
    personal_numbers: Optional[List[str]] = None
