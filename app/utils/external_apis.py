# app/utils/external_apis.py

from mimetypes import guess_extension
from dateutil.relativedelta import relativedelta
from flask import current_app
import requests
import logging
import re
from datetime import datetime, timedelta, timezone
from app.utils.file_manager import get_file_manager
from app.models import ContactData, CompanyData
from typing import List, Dict, Optional


def perform_google_search(search_query: str, search_type: str, username: str, max_results: int = 5) -> Dict:
    file_manager = get_file_manager()

    filename = f'{username}_{search_type}_google.json'
    existing_data = file_manager.load_json_file(filename)
    if existing_data:
        return existing_data

    print('Searching for file ', filename)

    run_input = {
        "queries": search_query,
        "resultsPerPage": max_results,
        "maxPagesPerQuery": 1,
        "languageCode": "",
        "mobileResults": False,
        "includeUnfilteredResults": False,
        "saveHtml": False,
        "saveHtmlToKeyValueStore": False,
        "includeIcons": False,
    }

    run = current_app.config['APIFY_CLIENT'].actor("nFJndFXA5zjCTuudP").call(run_input=run_input)

    results = {}
    for item in current_app.config['APIFY_CLIENT'].dataset(run["defaultDatasetId"]).iterate_items():
        results = item

    # Save the results to a file
    file_manager.save_file(results, filename, "json", username)

    return results


def search_company_about_page(company_website: str, contact_info: ContactData) -> Optional[List[Dict]]:
    """Searches for the About Us page of a company website"""
    search_query = f"site:{company_website} AND inurl:about -inurl:blog -inurl:support -inurl:article -inurl:articles"
    results = perform_google_search(search_query, "company_about", contact_info.linkedin_username)

    if not results or 'organicResults' not in results:
        return None

    return results['organicResults']


def search_company_case_studies(company_website: str, username: str) -> List[Dict]:
    """Search for case studies, testimonials, projects, reviews, or awards related to a company."""
    search_query = f"site:{company_website} AND (case study OR testimonial OR projects OR reviews OR award)"
    results = perform_google_search(search_query, "company_case_studies", username, max_results=10)

    if not results or 'organicResults' not in results:
        return []

    return [
        {
            'url': result['url'],
            'title': result['title'],
            'description': result.get('description', '')
        }
        for result in results['organicResults']
    ]


def search_person_interviews_podcasts(name: str, company_name: str, username: str, max_results: int = 10) -> List[Dict]:
    """
    Searches for interviews, podcasts, and articles featuring a person from a specific company.
    """
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    search_query = f'"{name}" AND "{company_name}" AND ("Interview" OR "podcast" OR "guest") after:{one_year_ago}'
    results = perform_google_search(search_query, "person_media", username, max_results)

    if not results or 'organicResults' not in results:
        return []

    return process_media_results(results['organicResults'], max_results)


def process_media_results(results: List[Dict], max_results: int) -> List[Dict]:
    """
    Process and prioritize media results based on recency and relevance.
    """
    current_date = datetime.now(timezone.utc)
    processed_results = []
    for result in results:
        result_date = extract_date(result)
        priority = determine_priority(result_date, current_date)

        if priority != 3:  # Exclude results older than a year
            processed_results.append({
                'title': result['title'],
                'url': result['url'],
                'description': result['description'],
                'date': result_date.isoformat() if result_date else None,
                'priority': priority
            })

    # Sort results by priority (lower number = higher priority)
    processed_results.sort(key=lambda x: (x['priority'], x['date'] or datetime.min.isoformat()), reverse=False)

    return processed_results[:max_results]


def extract_date(result: Dict) -> Optional[datetime]:
    if 'date' in result:
        try:
            return datetime.fromisoformat(result['date'].replace("Z", "+00:00"))
        except ValueError:
            pass

    date_match = re.search(r'\b(\d{1,2}\s+\w+\s+\d{4})\b', result['description'])
    if date_match:
        try:
            return datetime.strptime(date_match.group(1), '%d %b %Y')
        except ValueError:
            pass

    return None


def determine_priority(result_date: Optional[datetime], current_date: datetime) -> int:
    if not result_date:
        return 4  # Lowest priority if no date found

    time_difference = relativedelta(current_date, result_date)
    if time_difference.years > 0 or (time_difference.years == 0 and time_difference.months >= 12):
        return 3  # More than a year old
    elif time_difference.months >= 3:
        return 2  # Within the last year
    else:
        return 1  # Within the last 3 months


def get_nubela_data_for_user(linkedin_profile_url: str) -> Optional[Dict]:
    SUB_FOLDER = 'nubela'
    API_ENDPOINT = "https://nubela.co/proxycurl/api/v2/linkedin"
    LINKEDIN_USERNAME = linkedin_profile_url.split('/')[-2] if linkedin_profile_url.endswith('/') else \
        linkedin_profile_url.split('/')[-1]

    filename = f'{LINKEDIN_USERNAME}_nubela.json'
    file_manager = get_file_manager()

    # Check if we already have data for this user
    existing_data = file_manager.load_json_file(filename)
    if existing_data:
        existing_data['local_profile_pic_url'] = get_or_download_image(existing_data.get('profile_pic_url'),
                                                                       LINKEDIN_USERNAME, 'profile')
        existing_data['local_banner_pic_url'] = get_or_download_image(existing_data.get('background_cover_image_url'),
                                                                      LINKEDIN_USERNAME, 'banner')
        return existing_data

    params = {
        "linkedin_profile_url": linkedin_profile_url,
        "extra": "include"
    }

    # If not, fetch from API
    response = requests.get(API_ENDPOINT, params=params, headers={
        'Authorization': f'Bearer {current_app.config["NUBELA_API_KEY"]}'
    })

    if response.status_code == 200:
        data = response.json()

        # Store the data locally
        file_manager.save_file(data, filename, "json", LINKEDIN_USERNAME)

        data['local_profile_pic_url'] = get_or_download_image(data.get('profile_pic_url'), LINKEDIN_USERNAME, 'profile')
        data['local_banner_pic_url'] = get_or_download_image(data.get('background_cover_image_url'), LINKEDIN_USERNAME,
                                                             'banner')

        return data
    else:
        logging.error(f"Failed to fetch Nubela data for {linkedin_profile_url}: {response.status_code}")
        return None


def get_or_download_image(image_url: Optional[str], username: str, image_type: str) -> Optional[str]:
    if not image_url:
        return None

    file_manager = get_file_manager()
    existing_image = file_manager.get_frontend_image_url(f'{username}_{image_type}.*')
    if existing_image:
        return existing_image

    # If no existing file, download the image
    response = requests.get(image_url)
    if response.status_code == 200:
        content_type = response.headers.get('Content-Type', '').split(';')[0]
        ext = guess_extension(content_type)

        if not ext:
            logging.warning(
                f"Couldn't determine file extension for {image_type} image of {username}. Defaulting to .jpg")
            ext = '.jpg'

        filename = f'{username}_{image_type}{ext}'
        file_manager.save_file(response.content, filename, "image", username, is_frontend_image=True)
        return file_manager.get_frontend_image_url(filename)
    else:
        logging.error(f"Failed to download {image_type} image for {username}")
        return None
