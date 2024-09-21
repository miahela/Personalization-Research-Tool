from nameparser import HumanName

def filter_data(data):
    return [
        row for row in data 
        if not row.get('by the way', '').strip() and not row.get('approved', '').strip()
    ]

def process_important_fields(data):
    important_fields = [
        'contact_first_name', 'contact_last_name', 'contact_company_name',
        'contact_job_title', 'contact_profile_link', 'contact_image_link', 'contact_email'
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
            else:
                processed_row[field] = row.get(field, '')
        processed_data.append(processed_row)
    
    return processed_data

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