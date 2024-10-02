from datetime import datetime
from typing import List, Dict, Optional

from dateutil.relativedelta import relativedelta
from nameparser import HumanName
from cleanco import basename
from app.models import ContactData, CompanyData
from app.models.sheet_models import SheetRow


def filter_unprocessed_rows(rows: List[SheetRow]) -> List[SheetRow]:
    return [
        row for row in rows
        if not row.get('by the way', '').strip() and not row.get('approved', '').strip()
    ]


def process_contact_data(row: SheetRow, company_data: CompanyData, spreadsheet_id: str,
                         colored_cells: List[str]) -> ContactData:
    full_name = f"{row.get('contact_first_name', '')} {row.get('contact_last_name', '')}".strip()
    parsed_name = HumanName(full_name)

    linkedin_profile_url = row.get('contact_profile_link', '')
    linkedin_username = linkedin_profile_url.split('/')[-2] if linkedin_profile_url.endswith('/') else \
        linkedin_profile_url.split('/')[-1]

    return ContactData(
        contact_first_name=parsed_name.first,
        contact_last_name=parsed_name.last,
        contact_job_title=row.get('contact_job_title', ''),
        parsed_name=full_name,
        contact_company_name=row.get('contact_company_name', ''),
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


def process_company_name(company_name: str) -> str:
    return basename(company_name.strip().lower())


def process_pq_data(pq_rows: List[SheetRow]) -> Dict[str, str]:
    return {
        process_company_name(row.get('Company Name', '')): row.get('Website URL', '')
        for row in pq_rows
        if row.get('Company Name') and row.get('Website URL')
    }


def process_nubela_data(nubela_data: Dict[str, any]) -> Dict[str, any]:
    return {
        'bio': nubela_data.get('summary', ''),
        'headline': nubela_data.get('headline', ''),
        'industry': nubela_data.get('industry', ''),
        'profile_picture': nubela_data.get('local_profile_pic_url', ''),
        'banner_picture': nubela_data.get('local_banner_pic_url', ''),
        'languages': nubela_data.get('languages', []),
        'experiences': nubela_data.get('experiences', []),
        'volunteer_work': nubela_data.get('volunteer_work', []),
    }


def enrich_contact_data(contact: ContactData, nubela_data: Dict[str, any]) -> None:
    processed_nubela = process_nubela_data(nubela_data)
    for key, value in processed_nubela.items():
        setattr(contact, key, value)


def process_experiences(experiences: List[Dict[str, any]], current_company: str, current_job_title: str) -> List[
    Dict[str, str]]:
    current_date = datetime.now()

    def calculate_duration(start_date: Dict[str, int], end_date: Optional[Dict[str, int]] = None) -> relativedelta:
        start = datetime(start_date['year'], start_date['month'], start_date['day'])
        end = datetime(end_date['year'], end_date['month'], end_date['day']) if end_date else current_date
        return relativedelta(end, start)

    filtered_experiences = []
    for exp in experiences:
        if exp.get('ends_at') is None:  # Only consider ongoing experiences
            duration = calculate_duration(exp['starts_at'])

            is_current_role = (exp['title'].lower() == current_job_title.lower() and
                               duration.years == 0 and duration.months < 6)
            is_long_term_company = (exp['company'].lower() == current_company.lower() and
                                    duration.years >= 10)

            if is_current_role or is_long_term_company:
                filtered_experiences.append({
                    'company': exp['company'],
                    'title': exp['title'],
                    'duration': f"{duration.years} years, {duration.months} months"
                })

    # Remove duplicates
    return list({(exp['company'], exp['title']): exp for exp in filtered_experiences}.values())
