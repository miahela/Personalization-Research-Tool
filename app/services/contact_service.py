# app/services/contact_service.py

from datetime import datetime, timedelta
from typing import List, Optional

from cleanco import basename
from flask import current_app
from orjson import orjson
from tinydb import Query, TinyDB

from app.models import ContactData, CompanyData, SheetRow, PqKeywords
from app.models.contact_models import ExperiencesWithMetadata
from app.models.nubela_response_models import Experience, NubelaResponse
from app.utils.cleaning_utils import clean_name
from app.utils.external_apis import get_nubela_data_for_contact, search_person_interviews_podcasts, \
    search_company_case_studies, search_company_about_page


class ContactService:
    _instance = None

    def __init__(self):
        self.db = TinyDB(current_app.config['TINYDB_PATH'])
        self.contacts = self.db.table('contacts')

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_contact(self, linkedin_username: str) -> Optional[ContactData]:
        User = Query()
        # noinspection PyTypeChecker
        result = self.contacts.get(User.linkedin_username == linkedin_username)
        if result:
            return ContactData.model_validate(result)
        return None

    def create_or_update_contact(self, row: SheetRow, company_data: CompanyData, spreadsheet_id: str,
                                 colored_cells: List[str]) -> ContactData:
        contact_data = self._initialize_contact_data(row, company_data, spreadsheet_id, colored_cells)
        self._add_company_links(contact_data)
        self._add_media_links(contact_data)
        self._add_nubela_data(contact_data)

        existing_contact = self.get_contact(contact_data.linkedin_username)
        if existing_contact:
            # noinspection PyTypeChecker
            self.contacts.update(contact_data.model_dump(), Query().linkedin_username == contact_data.linkedin_username)
        else:
            # Create new contact
            self.contacts.insert(contact_data.model_dump())

        return contact_data

    def save_contact(self, contact: ContactData):
        User = Query()
        # noinspection PyTypeChecker
        existing = self.contacts.get(User.linkedin_username == contact.linkedin_username)
        if existing:
            # noinspection PyTypeChecker
            self.contacts.update(orjson.loads(contact.model_dump_json()),
                                 User.linkedin_username == contact.linkedin_username)
        else:
            self.contacts.insert(orjson.loads(contact.model_dump_json()))

    @staticmethod
    def _initialize_contact_data(row: SheetRow, company_data: CompanyData, spreadsheet_id: str,
                                 colored_cells: List[str]) -> ContactData:
        full_name = f"{row.get('contact_first_name', '')} {row.get('contact_last_name', '')}".strip()
        parsed_name = clean_name(full_name)

        linkedin_profile_url = row.get('contact_profile_link', '')
        linkedin_username = linkedin_profile_url.split('/')[-2] if linkedin_profile_url.endswith('/') else \
            linkedin_profile_url.split('/')[-1]

        return ContactData(
            contact_first_name=parsed_name['first_name'],
            contact_last_name=parsed_name['last_name'],
            contact_job_title=row.get('contact_job_title', ''),
            parsed_name=full_name,
            contact_company_name=basename(row.get('contact_company_name', '')),
            hook_name=row.get('hook_name', ''),
            messenger_campaign_instance=row.get('messenger_campaign_instance', ''),
            company=company_data,
            contact_profile_link=linkedin_profile_url,
            linkedin_username=linkedin_username,
            profile_picture=row.get('contact_image_link'),
            colored_cells=colored_cells,
            spreadsheet_id=spreadsheet_id,
            row_number=row.row_number
        )

    @staticmethod
    def _add_company_links(contact_data: ContactData):
        if contact_data.company.website:
            about_links = search_company_about_page(contact_data.company.website, contact_data)
            case_study_links = search_company_case_studies(contact_data.company.website, contact_data.linkedin_username)
            contact_data.company.about_links = about_links[:3] if about_links else []
            contact_data.company.case_study_links = case_study_links if case_study_links else []

    @staticmethod
    def _add_media_links(contact_data: ContactData):
        media_links = search_person_interviews_podcasts(contact_data.parsed_name, contact_data.company.name,
                                                        contact_data.linkedin_username)
        contact_data.interviews_and_podcasts = media_links if media_links else []

    @staticmethod
    def _add_nubela_data(contact_data: ContactData):
        if contact_data.contact_profile_link:
            nubela_data_and_pictures = get_nubela_data_for_contact(contact_data.contact_profile_link)
            nubela_data: NubelaResponse = nubela_data_and_pictures.get('nubela_response')
            profile_picture = nubela_data_and_pictures.get('local_profile_pic_url')
            banner_picture = nubela_data_and_pictures.get('local_banner_pic_url')

            if profile_picture:
                contact_data.profile_picture = profile_picture

            if banner_picture:
                contact_data.banner_picture = banner_picture

            if nubela_data:
                contact_data.bio = nubela_data.summary
                contact_data.headline = nubela_data.headline
                contact_data.industry = nubela_data.industry
                contact_data.languages = nubela_data.languages
                contact_data.volunteer_work = nubela_data.volunteer_work
                contact_data.nubela_response = nubela_data

    def add_relevant_experience(self, contact_data: ContactData, keywords: PqKeywords) -> None:
        if contact_data.nubela_response and contact_data.nubela_response.experiences:
            contact_data.relevant_experiences = self._get_relevant_experience(
                contact_data.nubela_response.experiences,
                contact_data.contact_job_title,
                contact_data.company.name,
                keywords
            )
            print(contact_data.linkedin_username, contact_data.relevant_experiences)

    @staticmethod
    def _get_relevant_experience(experiences_data: List[Experience], contact_job_title: str, current_company: str,
                                 keywords: PqKeywords) -> ExperiencesWithMetadata:
        relevant_experiences = []
        most_likely_current_title = contact_job_title
        title_mismatch = False

        # Sort experiences by start date, most recent first
        sorted_experiences = sorted(
            [exp for exp in experiences_data if exp.get_start_date() is not None],
            key=lambda x: x.get_start_date(),
            reverse=True
        )

        # Filter present experiences
        present_experiences = [exp for exp in sorted_experiences if exp.is_current]

        # Determine the correct job title
        if present_experiences:
            most_likely_current_title = present_experiences[0].title
            if most_likely_current_title.lower() != contact_job_title.lower():
                title_mismatch = True

        for exp in sorted_experiences:
            start_date = exp.get_start_date()
            if start_date is None:
                continue  # Skip experiences without a valid start date

            # Check if the experience is relevant based on the new criteria
            is_relevant = (
                    (exp.is_current and exp.title == most_likely_current_title and exp.duration <= timedelta(
                        days=180)) or
                    (exp.company.lower() == current_company.lower() and exp.duration >= timedelta(days=3650))
                # 10 years
            )

            if is_relevant and exp.matches_keywords(keywords):
                relevant_experiences.append(exp)

        return ExperiencesWithMetadata(experiences=relevant_experiences, title_mismatch=title_mismatch,
                                       most_likely_current_title=most_likely_current_title)
