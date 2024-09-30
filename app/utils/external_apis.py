from glob import glob
from mimetypes import guess_extension
from typing import IO, List, Dict
from apify_client import ApifyClient
from dateutil.relativedelta import relativedelta
from flask import current_app
import requests
import orjson
import os
import logging
import re
from datetime import datetime, timedelta, timezone

DATA_DIR = 'user_data'
IMAGE_DIR = 'app/static/images'

def load_json_file(filename):
    with open(filename, 'rb') as f:
        return orjson.loads(f.read())


def get_or_load_data(folder, filename, process_func=None):
    full_path = os.path.join(folder, filename)
    data = load_json_file(full_path)
    return process_func(data) if process_func else data


def save_json_file(data, filename):
    with open(filename, 'wb') as f:
        f.write(orjson.dumps(data))


def sanitize_filename(filename):
    """
    Sanitize the filename by replacing problematic characters with underscores
    and truncating if necessary.
    """
    # Replace any non-alphanumeric characters (except underscores) with underscores
    sanitized = re.sub(r'[^\w\-_. ]', '_', filename)
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    # Truncate to a reasonable length if needed (e.g., 200 characters)
    return sanitized[:200]


def perform_google_search(search_query, search_type, max_results=5):
    # Create a subdirectory for Google search results
    SUB_FOLDER = 'google_search'
    os.makedirs(f'{DATA_DIR}/{SUB_FOLDER}', exist_ok=True)

    # Generate a filename based on the search query
    sanitized_query = sanitize_filename(search_query)
    filename = f'{DATA_DIR}/{SUB_FOLDER}/{search_type}_{sanitized_query}.json'

    # Check if we already have data for this search
    if os.path.exists(filename):
        return load_json_file(filename)

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
    save_json_file(results, filename)

    return results


def score_search_result(result, keywords):
    """Score a single search result based on keyword matches"""
    score = 0
    combined_text = f"{result['title']} {result['displayedUrl']} {result['description']}".lower()

    for keyword in keywords:
        if keyword.lower() in combined_text:
            score += 1

    return score


def extract_best_result(results, contact_info):
    """Extract the best result based on keyword matches"""
    keywords = [
        contact_info['contact_first_name'],
        contact_info['contact_last_name'],
        contact_info['contact_job_title'],
        'linkedin.com',  # Check for LinkedIn profile links
        '@'  # Simple check for email addresses
    ]

    # Remove any empty keywords
    keywords = [k for k in keywords if k]

    scored_results = []
    for result in results:
        score = score_search_result(result, keywords)
        scored_results.append((score, result))

    # Sort by score (descending) and then by position (ascending)
    scored_results.sort(key=lambda x: (-x[0], x[1]['position']))

    if scored_results:
        best_score, best_result = scored_results[0]
        return best_result
    return None


def search_company_about_page(company_website, contact_info):
    """Searches for the About Us page of a company website"""
    search_query = f"site:{company_website} AND inurl:about -inurl:blog -inurl:support -inurl:article -inurl:articles"
    print(search_query)
    results = perform_google_search(search_query, "company_about")

    if not results:
        return None

    # best_result = extract_best_result(results['organicResults'], contact_info)
    # print(best_result)
    # return best_result

    if results['organicResults']:
        return results['organicResults'][0]
    else:
        return None


def search_person_interviews_podcasts(name, company_name, max_results=10):
    """
    Searches for interviews, podcasts, and articles featuring a person from a specific company.

    :param name: Full name of the person
    :param company_name: Name of the company
    :param max_results: Maximum number of results to return (default 10)
    :return: List of relevant search results
    """
    # Modify the search query to include a date filter for the last year using the after: parameter
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    search_query = f'"{name}" AND "{company_name}" AND ("Interview" OR "podcast" OR "guest") after:{one_year_ago}'
    # TODO: Modify the query for better results, currently it's not giving very accurate results
    results = perform_google_search(search_query, "person_media", max_results)

    if not results:
        return []

    return process_media_results(results['organicResults'], max_results)


def process_media_results(results, max_results):
    """
    Process and prioritize media results based on recency and relevance.

    Priority 1: Within the last 3 months (top priority)
    Priority 2: Within the last year
    Priority 3: Older than a year
    Priority 4: No date found

    :param results: List of search results
    :param max_results: Maximum number of results to return
    :return: List of prioritized and processed results
    """
    current_date = datetime.now(timezone.utc)
    processed_results = []
    for result in results:
        # Extract date if available
        if 'date' in result:
            try:
                result_date = datetime.fromisoformat(result['date'].replace("Z", "+00:00"))
            except ValueError:
                result_date = None
        else:
            date_match = re.search(r'\b(\d{1,2}\s+\w+\s+\d{4})\b', result['description'])
            if date_match:
                try:
                    result_date = datetime.strptime(date_match.group(1), '%d %b %Y')
                except ValueError:
                    result_date = None
            else:
                result_date = None

        # Determine priority
        if result_date:
            time_difference = relativedelta(current_date, result_date)
            if time_difference.years > 0 or (time_difference.years == 0 and time_difference.months >= 12):
                priority = 3  # More than a year old - Discard
            elif time_difference.months >= 3:
                priority = 2  # Within the last year
            else:
                priority = 1  # Within the last 3 months
        else:
            priority = 4  # Lowest priority if no date found

        if priority != 3:
            processed_results.append({
                'title': result['title'],
                'url': result['url'],
                'description': result['description'],
                'date': result_date,
                'priority': priority
            })

    # Sort results by priority (lower number = higher priority)
    processed_results.sort(key=lambda x: (x['priority'], x['date'] if x['date'] else datetime.min), reverse=False)

    return processed_results[:max_results]


def search_person_info(person_name, company_name):
    """Searches for information about a person related to a company"""
    search_query = f'"{person_name}" AND "{company_name}"'
    return perform_google_search(search_query, "person_info")


# Additional helper function to extract potential contact information
def extract_contact_info(result):
    """Attempt to extract contact information from a search result"""
    info = {}

    # Simple email extraction (this can be improved with more robust regex)
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', result['description'])
    if email_match:
        info['email'] = email_match.group(0)

    # Check for LinkedIn profile in URL
    if 'linkedin.com/in/' in result['url']:
        info['linkedin_profile'] = result['url']

    # You can add more extraction logic here as needed

    return info


def get_nubela_data_for_user(linkedin_profile_url):
    SUB_FOLDER = 'nubela'
    API_ENDPOINT = "https://nubela.co/proxycurl/api/v2/linkedin"
    LINKEDIN_USERNAME = linkedin_profile_url.split('/')[-2] if linkedin_profile_url.endswith('/') else \
        linkedin_profile_url.split('/')[-1]

    """Fetch user data from API or local storage"""
    filename = f'{DATA_DIR}/{SUB_FOLDER}/{LINKEDIN_USERNAME}.json'

    # Check if we already have data for this user
    if os.path.exists(filename):
        data = load_json_file(filename)
        data['local_profile_pic_url'] = get_or_download_image(data.get('profile_pic_url'), LINKEDIN_USERNAME,
                                                              'profile')
        data['local_banner_pic_url'] = get_or_download_image(data.get('background_cover_image_url'),
                                                             LINKEDIN_USERNAME, 'banner')
        return data

    params = {
        "linkedin_profile_url": linkedin_profile_url,
        "extra": "include"
    }
    print(params)
    # If not, fetch from API
    response = requests.get(API_ENDPOINT, params=params, headers={
        'Authorization': f'Bearer {current_app.config["NUBELA_API_KEY"]}'
    })

    print(response)

    if response.status_code == 200:
        data = response.json()

        # Store the data locally
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(f'{DATA_DIR}/{SUB_FOLDER}', exist_ok=True)

        save_json_file(data, filename)

        data['local_profile_pic_url'] = get_or_download_image(data.get('profile_pic_url'), LINKEDIN_USERNAME, 'profile')
        data['local_banner_pic_url'] = get_or_download_image(data.get('background_cover_image_url'), LINKEDIN_USERNAME,
                                                             'banner')

        return data
    else:
        return None


def get_or_download_image(image_url, username, image_type):
    if not image_url:
        return None

    # Check if we already have a file for this user and image type
    existing_files = glob(os.path.join(IMAGE_DIR, f'{username}_{image_type}.*'))
    if existing_files:
        # Return the path of the first matching file
        return f'/static/images/{os.path.basename(existing_files[0])}'

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
        filepath = os.path.join(IMAGE_DIR, filename)

        os.makedirs(IMAGE_DIR, exist_ok=True)

        with open(filepath, 'wb') as f:
            f.write(response.content)

        return f'/static/images/{filename}'
    else:
        logging.error(f"Failed to download {image_type} image for {username}")
        return None
