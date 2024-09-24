import re

from flask import render_template, request, jsonify
from app import app
from app.utils.google_drive import list_files_in_folder
from app.utils.google_sheets import get_sheet_data, update_sheet_data, get_sheet_names
from app.utils.data_processor import filter_data, process_name, extract_personalization_data, process_nubela_data
from app.utils.external_apis import get_linkedin_data, get_nubela_data_for_user, search_company_about_page, \
    search_person_interviews_podcasts
from app.utils.google_drive import process_sheets_in_folder
import logging

from app.utils.google_drive import list_files_in_folder
from app.utils.google_sheets import get_sheet_data, get_sheet_names
from app.utils.data_processor import filter_data, process_new_connections, process_pq

FOLDER_ID = '1IEQ4Vm1sxGCVJG2p_nwvH9iE7TDyyUgS'


@app.route('/')
def index():
    sheets = list_files_in_folder(FOLDER_ID) 
    return render_template('index.html', sheets=sheets)


@app.route('/process', methods=['POST'])
def process_sheets():
    spreadsheet_id = request.json.get('sheet_id')

    # Process New Connections sheet
    new_connections_data = get_sheet_data(spreadsheet_id, 'New Connections', 'A:ZZ')

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
            # Remove 'https://www.' or 'http://www.' from the beginning of the website URL
            clean_website = re.sub(r'^https?://www\.', '', company_website)
            # Perform the search
            company_links = search_company_about_page(clean_website, row)

            if company_links:
                # Add the search results to the row data
                row['company_about_link'] = {
                    'title': company_links.get('title', ''),
                    'url': company_links.get('url', ''),
                    'description': company_links.get('description', ''),
                }

        media_links = search_person_interviews_podcasts(full_name, company_name)
        if media_links:
            row['interviews_and_podcasts'] = []
            for link in media_links:
                row['interviews_and_podcasts'].append({
                    'url': link.get('url', ''),
                    'description': link.get('description', ''),
                    'date': link.get('date', ''),
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
        'pq_data': pq_important_data,
    })


@app.route('/save', methods=['POST'])
def save_data():
    sheet_id = request.form['sheet_id']
    data = request.json['data']
    result = update_sheet_data(sheet_id, 'A1:Z', data)  # Adjust range as needed
    return jsonify({'success': True, 'updated_cells': result.get('updatedCells')})
