import re

from flask import render_template, request, jsonify
from app import app
from app.utils.google_drive import list_files_in_folder
from app.utils.google_sheets import get_sheet_data, get_sheet_names, get_colored_cells, update_specific_cells
from app.utils.data_processor import filter_data, process_name, extract_personalization_data, process_nubela_data
from app.utils.external_apis import get_nubela_data_for_user, search_company_about_page, \
    search_person_interviews_podcasts, search_company_case_studies  # Add the new import
import logging

from app.utils.google_drive import list_files_in_folder
from app.utils.google_sheets import get_sheet_data, get_sheet_names
from app.utils.data_processor import filter_data, process_new_connections, process_pq

FOLDER_ID = '13qlaX_eHBkMV60JaszK_JgqjQVhb1mVI'


@app.route('/')
def index():
    sheets = list_files_in_folder(FOLDER_ID)
    return render_template('index.html', sheets=sheets)


@app.route('/process', methods=['POST'])
def process_sheets():
    spreadsheet_id = request.json.get('sheet_id')

    # Process New Connections sheet
    new_connections_data = get_sheet_data(spreadsheet_id, 'New Connections', 'A:ZZ')
    colored_cells = get_colored_cells(spreadsheet_id, 'New Connections')

    if new_connections_data is None or len(new_connections_data) < 2:
        return jsonify({'error': 'No data found in New Connections sheet or sheet does not exist'}), 404

    headers = new_connections_data[0]
    processed_data = [dict(zip(headers, row + [''] * (len(headers) - len(row)))) for row in new_connections_data[1:]]

    filtered_data = filter_data(processed_data)
    important_data = process_new_connections(filtered_data)

    # Process PQ sheet
    sheet_names = get_sheet_names(spreadsheet_id)
    pq_sheet_name = next((name for name in sheet_names if name.endswith('PQ')), None)

    if pq_sheet_name:
        pq_data = get_sheet_data(spreadsheet_id, pq_sheet_name, 'A:ZZ')
        if pq_data and len(pq_data) > 1:
            pq_headers = pq_data[0]
            pq_processed_data = [dict(zip(pq_headers, row + [''] * (len(pq_headers) - len(row)))) for row in
                                 pq_data[1:]]
            pq_important_data = process_pq(pq_processed_data)
        else:
            pq_important_data = {}
    else:
        pq_important_data = {}

    # Google searches
    for row in important_data:
        company_name = row.get('contact_company_name', '').strip().lower()
        full_name = f"{row.get('contact_first_name', '').strip()} {row.get('contact_last_name', '').strip()}".strip()
        company_website = pq_important_data.get(company_name, '')
        if not company_name:
            continue

        if company_website:
            row['company_website'] = company_website
            clean_website = re.sub(r'^https?://www\.', '', company_website)
            company_links = search_company_about_page(clean_website, row)

            if company_links:
                row['company_about_link'] = []
                for link in company_links[:3]:
                    row['company_about_link'].append({
                        'title': link.get('title', ''),
                        'url': link.get('url', ''),
                        'description': link.get('description', ''),
                    })
                    logging.info(f"About page links for {company_name}: {link.get('url')}")  # Add this line

            case_study_links = search_company_case_studies(clean_website)
            if case_study_links:
                row['case_study_links'] = case_study_links
                logging.info(f"Case study links for {company_name}: {case_study_links}")  # Add this line

        media_links = search_person_interviews_podcasts(full_name, company_name)
        if media_links:
            row['interviews_and_podcasts'] = []
            for link in media_links:
                row['interviews_and_podcasts'].append({
                    'url': link.get('url', ''),
                    'title': link.get('title', ''),
                    'date': link.get('date', ''),
                    'description': link.get('description', ''),
                })

    # Nubela API call
    for row in important_data:
        linkedin_profile_url = row.get('contact_profile_link', '')
        if linkedin_profile_url:
            nubela_data = get_nubela_data_for_user(linkedin_profile_url)
            if nubela_data:
                row.update(process_nubela_data(nubela_data))

    logging.info(f"Number of rows after processing New Connections: {len(important_data)}")
    logging.info(f"Number of rows after processing PQ sheet: {len(pq_important_data)}")

    return jsonify({
        'new_connections': important_data,
        'colored_cells': colored_cells,
        'pq_data': pq_important_data,
        'total_items': len(important_data)  # Add this line
    })


# TODO: Add total items to the frontend


@app.route('/save', methods=['POST'])
def save_data():
    sheet_id = request.json.get('sheet_id')
    row_number = request.json.get('row_number')
    entry_data = request.json.get('entry_data')
    result = update_specific_cells(sheet_id, 'New Connections', row_number, entry_data)  # Adjust range as needed
    return jsonify({'success': True, 'updated_cells': result.get('updatedCells')})
