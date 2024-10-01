from nameparser import HumanName
from cleanco import basename

def filter_data(data):
    return [
        row for row in data
        if not row.get('by the way', '').strip() and not row.get('approved', '').strip()
    ]


def process_new_connections(data):
    important_fields = [
        'contact_first_name', 'contact_last_name', 'contact_company_name',
        'contact_job_title', 'contact_profile_link', 'contact_image_link', 'contact_email',
        "messenger_campaign_instance", "hook_name", "row_number"
    ]

    processed_data = []
    for row in data:
        processed_row = {}
        for field in important_fields:
            if field in ['contact_first_name', 'contact_last_name']:
                full_name = f"{row.get('contact_first_name', '')} {row.get('contact_last_name', '')}".strip()
                parsed_name = HumanName(full_name)
                processed_row['contact_first_name'] = parsed_name.first
                processed_row['contact_last_name'] = parsed_name.last
            elif field == 'contact_company_name':
                processed_row[field] = basename(row.get(field, ''))
            else:
                processed_row[field] = row.get(field, '')
        linkedin_profile_url = processed_row.get('contact_profile_link', '')
        LINKEDIN_USERNAME = linkedin_profile_url.split('/')[-2] if linkedin_profile_url.endswith('/') else \
            linkedin_profile_url.split('/')[-1]
        processed_row['linkedin_username'] = LINKEDIN_USERNAME
        if processed_row['contact_first_name'] and processed_row['contact_last_name']:
            processed_data.append(processed_row)

    return processed_data

def process_pq(data):
    processed_data = {}
    for row in data:
        company_name = basename(row.get('Company Name', '')).strip().lower()
        if company_name:
            processed_data[company_name] = row.get('Website URL', '')

    return processed_data

def process_nubela_data(data):
    return {
        'bio': data.get('summary', ''),
        'headline': data.get('headline', ''),
        'industry': data.get('industry', ''),
        'profile_picture': data.get('local_profile_pic_url', ''),
        'banner_picture': data.get('local_banner_pic_url', ''),
        'languages': data.get('languages', []),
        "experiences": data.get('experiences', []),
        "volunteer_work": data.get('volunteer_work', []),
    }

def process_name(full_name):
    name = HumanName(full_name)
    return f"{name.first} {name.last}"

def extract_personalization_data(row):
    # Implement logic to extract personalization columns
    # This is a placeholder implementation
    return {
        'job_title_plural': row[3] if len(row) > 3 else '',
        'customer_plural': row[4] if len(row) > 4 else '',
        # Add more as needed
    }
