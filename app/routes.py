from flask import render_template, request, jsonify
from app import app
from app.utils.google_drive import list_files_in_folder
from app.utils.google_sheets import get_sheet_data, update_sheet_data
from app.utils.data_processor import filter_data, process_name, extract_personalization_data
from app.utils.external_apis import search_google, get_linkedin_data
from app.utils.google_drive import process_sheets_in_folder
import logging

FOLDER_ID = '1IEQ4Vm1sxGCVJG2p_nwvH9iE7TDyyUgS'

# @app.route('/process_sheets')
# def process_sheets():
#     all_sheets_data = process_sheets_in_folder(FOLDER_ID)
#     return jsonify(all_sheets_data)

@app.route('/')
def index():
    sheets = list_files_in_folder(FOLDER_ID)
    return render_template('index.html', sheets=sheets)

@app.route('/process', methods=['POST'])
def process_sheets():
    spreadsheet_id = request.form['sheet_id']
    data = get_sheet_data(spreadsheet_id, 'New Connections', 'A:ZZ')
    
    if data is None or len(data) < 2:  # Check if we have headers and at least one row
        return jsonify({'error': 'No data found or sheet does not exist'}), 404
    
    headers = data[0]
    processed_data = [dict(zip(headers, row + [''] * (len(headers) - len(row)))) for row in data[1:]]
    
    logging.info(f"Number of rows before filtering: {len(processed_data)}")
    logging.info(f"Columns: {headers}")
    
    filtered_data = filter_data(processed_data)
    
    logging.info(f"Number of rows after filtering: {len(filtered_data)}")
    
    for i, row in enumerate(filtered_data[:5]):
        logging.info(f"Sample row {i}: {row}")
    
    return jsonify(filtered_data)

@app.route('/save', methods=['POST'])
def save_data():
    sheet_id = request.form['sheet_id']
    data = request.json['data']
    result = update_sheet_data(sheet_id, 'A1:Z', data)  # Adjust range as needed
    return jsonify({'success': True, 'updated_cells': result.get('updatedCells')})