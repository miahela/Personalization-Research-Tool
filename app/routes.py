import json
import re
from flask import render_template, request, jsonify, current_app, Response, stream_with_context
from app import app
from app.utils.file_manager import get_file_manager
from app.utils.google_drive import list_files_in_folder
from app.utils.google_sheets import get_sheet_data, get_sheet_names, get_colored_cells, update_specific_cells
from app.utils.data_processor import filter_data, process_name, extract_personalization_data, process_nubela_data
from app.utils.external_apis import get_nubela_data_for_user, search_company_about_page, \
    search_person_interviews_podcasts, search_company_case_studies  # Add the new import
import logging
from datetime import datetime
from app.utils.google_drive import list_files_in_folder
from app.utils.google_sheets import get_sheet_data, get_sheet_names
from app.utils.data_processor import filter_data, process_new_connections, process_pq
import traceback

FOLDER_ID = '13qlaX_eHBkMV60JaszK_JgqjQVhb1mVI'


def count_empty_by_the_way_rows(spreadsheet_id):
    new_connections_data = get_sheet_data(spreadsheet_id, 'New Connections', 'A:ZZ')

    if new_connections_data is None or len(new_connections_data) < 2:
        return 0

    headers = new_connections_data[0]
    processed_data = [dict(zip(headers, row + [''] * (len(headers) - len(row)))) for row in new_connections_data[1:]]
    filtered_data = filter_data(processed_data)

    return len(filtered_data)


@app.route('/')
def index():
    sheets = list_files_in_folder(FOLDER_ID)
    sheets_with_counts = []

    for sheet in sheets:
        count = count_empty_by_the_way_rows(sheet['id'])
        sheets_with_counts.append({
            'id': sheet['id'],
            'name': sheet['name'],
            'empty_by_the_way_count': count
        })

    return render_template('index.html', sheets=sheets_with_counts)


# def process_single_spreadsheet(spreadsheet_id):
#     result = {
#         'spreadsheet_id': spreadsheet_id,
#         'new_connections': [],
#         'colored_cells': [],
#         'pq_data': {},
#         'total_items': 0
#     }
#
#     # Process New Connections sheet
#     new_connections_data = get_sheet_data(spreadsheet_id, 'New Connections', 'A:ZZ')
#     result['colored_cells'] = get_colored_cells(spreadsheet_id, 'New Connections')
#
#     if new_connections_data is None or len(new_connections_data) < 2:
#         result['error'] = 'No data found in New Connections sheet or sheet does not exist'
#         return result
#
#     headers = new_connections_data[0]
#     processed_data = [dict(zip(headers, row + [''] * (len(headers) - len(row)))) for row in new_connections_data[1:]]
#
#     filtered_data = filter_data(processed_data)
#     important_data = process_new_connections(filtered_data)
#
#     # Process PQ sheet
#     sheet_names = get_sheet_names(spreadsheet_id)
#     pq_sheet_name = next((name for name in sheet_names if name.endswith('PQ')), None)
#
#     if pq_sheet_name:
#         pq_data = get_sheet_data(spreadsheet_id, pq_sheet_name, 'A:ZZ')
#         if pq_data and len(pq_data) > 1:
#             pq_headers = pq_data[0]
#             pq_processed_data = [dict(zip(pq_headers, row + [''] * (len(pq_headers) - len(row)))) for row in
#                                  pq_data[1:]]
#             result['pq_data'] = process_pq(pq_processed_data)
#         else:
#             result['pq_data'] = {}
#     else:
#         result['pq_data'] = {}
#
#     # Google searches and Nubela API calls
#     for row in important_data:
#         row['spreadsheet_id'] = spreadsheet_id
#         row['colored_cells'] = result['colored_cells']
#
#         company_name = row.get('contact_company_name', '').strip().lower()
#         full_name = f"{row.get('contact_first_name', '').strip()} {row.get('contact_last_name', '').strip()}".strip()
#         company_website = result['pq_data'].get(company_name, '')
#
#         if company_name and company_website:
#             row['company_website'] = company_website
#             clean_website = re.sub(r'^https?://www\.', '', company_website)
#             company_links = search_company_about_page(clean_website, row)
#
#             if company_links:
#                 row['company_about_link'] = []
#                 for link in company_links[:3]:
#                     row['company_about_link'].append({
#                         'title': link.get('title', ''),
#                         'url': link.get('url', ''),
#                         'description': link.get('description', ''),
#                     })
#                     logging.info(f"About page links for {company_name}: {link.get('url')}")
#
#             case_study_links = search_company_case_studies(clean_website, row['linkedin_username'])
#             if case_study_links:
#                 row['case_study_links'] = case_study_links
#                 logging.info(f"Case study links for {company_name}: {case_study_links}")
#
#         media_links = search_person_interviews_podcasts(full_name, company_name, row['linkedin_username'])
#         if media_links:
#             row['interviews_and_podcasts'] = []
#             for link in media_links:
#                 row['interviews_and_podcasts'].append({
#                     'url': link.get('url', ''),
#                     'title': link.get('title', ''),
#                     'date': link.get('date', ''),
#                     'description': link.get('description', ''),
#                 })
#
#         linkedin_profile_url = row.get('contact_profile_link', '')
#         if linkedin_profile_url:
#             nubela_data = get_nubela_data_for_user(linkedin_profile_url)
#             if nubela_data:
#                 row.update(process_nubela_data(nubela_data))
#
#     result['new_connections'] = important_data
#     result['total_items'] = len(important_data)
#
#     logging.info(
#         f"Spreadsheet {spreadsheet_id}: Number of rows after processing New Connections: {len(important_data)}")
#     logging.info(f"Spreadsheet {spreadsheet_id}: Number of rows after processing PQ sheet: {len(result['pq_data'])}")
#
#     return result

def process_single_spreadsheet(spreadsheet_id, batch_size=2):
    result = {
        'spreadsheet_id': spreadsheet_id,
        'new_connections': [],
        'colored_cells': [],
        'pq_data': {},
        'total_items': 0
    }

    # Process New Connections sheet
    new_connections_data = get_sheet_data(spreadsheet_id, 'New Connections', 'A:ZZ')
    result['colored_cells'] = get_colored_cells(spreadsheet_id, 'New Connections')

    if new_connections_data is None or len(new_connections_data) < 2:
        result['error'] = 'No data found in New Connections sheet or sheet does not exist'
        yield result
        return

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
            result['pq_data'] = process_pq(pq_processed_data)
        else:
            result['pq_data'] = {}
    else:
        result['pq_data'] = {}

    # Process rows in batches
    for i in range(0, len(important_data), batch_size):
        batch = important_data[i:i + batch_size]
        processed_batch = []

        for row in batch:
            row['spreadsheet_id'] = spreadsheet_id
            row['colored_cells'] = result['colored_cells']

            company_name = row.get('contact_company_name', '').strip().lower()
            full_name = f"{row.get('contact_first_name', '').strip()} {row.get('contact_last_name', '').strip()}".strip()
            company_website = result['pq_data'].get(company_name, '')

            if company_name and company_website:
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
                        logging.info(f"About page links for {company_name}: {link.get('url')}")

                case_study_links = search_company_case_studies(clean_website, row['linkedin_username'])
                if case_study_links:
                    row['case_study_links'] = case_study_links
                    logging.info(f"Case study links for {company_name}: {case_study_links}")

            media_links = search_person_interviews_podcasts(full_name, company_name, row['linkedin_username'])
            if media_links:
                row['interviews_and_podcasts'] = []
                for link in media_links:
                    row['interviews_and_podcasts'].append({
                        'url': link.get('url', ''),
                        'title': link.get('title', ''),
                        'date': link.get('date', ''),
                        'description': link.get('description', ''),
                    })

            linkedin_profile_url = row.get('contact_profile_link', '')
            if linkedin_profile_url:
                nubela_data = get_nubela_data_for_user(linkedin_profile_url)
                if nubela_data:
                    row.update(process_nubela_data(nubela_data))

            processed_batch.append(row)

        result['new_connections'] = processed_batch
        result['total_items'] = len(processed_batch)
        yield result

    logging.info(
        f"Spreadsheet {spreadsheet_id}: Number of rows after processing New Connections: {len(important_data)}")
    logging.info(f"Spreadsheet {spreadsheet_id}: Number of rows after processing PQ sheet: {len(result['pq_data'])}")


def process_single_spreadsheet_with_context(spreadsheet_id):
    with app.app_context():
        yield from process_single_spreadsheet(spreadsheet_id)


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


@app.route('/process_stream', methods=['GET'])
def process_sheets_stream():
    spreadsheet_ids = request.args.getlist('sheet_id')

    if not spreadsheet_ids:
        return Response('{"error": "No spreadsheet IDs provided"}', status=400, mimetype='application/json')

    def generate():
        all_new_connections = []
        all_colored_cells = []
        all_pq_data = {}
        total_items = 0
        errors = []
        processed_count = 0

        for spreadsheet_id in spreadsheet_ids:
            try:
                logging.debug(f"Processing spreadsheet: {spreadsheet_id}")
                for batch_result in process_single_spreadsheet_with_context(spreadsheet_id):
                    all_new_connections.extend(batch_result['new_connections'])
                    all_colored_cells.extend(batch_result['colored_cells'])
                    all_pq_data.update(batch_result['pq_data'])
                    total_items += batch_result['total_items']

                    batch_data = {
                        'new_connections': batch_result['new_connections'],
                        'colored_cells': batch_result['colored_cells'],
                        'pq_data': batch_result['pq_data'],
                        'total_items': total_items,
                        'errors': errors,
                        'processed_count': processed_count,
                        'total_count': len(spreadsheet_ids)
                    }
                    yield f"data: {json.dumps(batch_data, cls=CustomJSONEncoder)}\n\n"
                    logging.debug(f"Yielded batch for spreadsheet {spreadsheet_id}")

                processed_count += 1

            except Exception as exc:
                error_message = f'Spreadsheet {spreadsheet_id} generated an exception: {str(exc)}'
                errors.append(error_message)
                logging.error(f"Error processing spreadsheet {spreadsheet_id}: {exc}")
                logging.error(traceback.format_exc())
                yield f"data: {json.dumps({'error': error_message}, cls=CustomJSONEncoder)}\n\n"

        # Send a final message to indicate processing is complete
        yield f"data: {json.dumps({'complete': True}, cls=CustomJSONEncoder)}\n\n"
        logging.debug("Processing complete, sent final message")

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/save', methods=['POST'])
def save_data():
    sheet_id = request.json.get('sheet_id')
    row_number = request.json.get('row_number')
    entry_data = request.json.get('entry_data')
    result = update_specific_cells(sheet_id, 'New Connections', row_number, entry_data)  # Adjust range as needed

    username = request.json.get('username')
    file_manager = get_file_manager()
    file_manager.delete_all_files_by_user(username)

    return jsonify({'success': True, 'updated_cells': result.get('updatedCells')})
