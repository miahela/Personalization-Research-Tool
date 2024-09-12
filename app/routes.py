from flask import render_template, request, jsonify
from app import app
from app.utils.google_drive import list_files_in_folder
from app.utils.google_sheets import get_sheet_data, update_sheet_data
from app.utils.data_processor import filter_data, process_name, extract_personalization_data
from app.utils.external_apis import search_google, get_linkedin_data

FOLDER_ID = 'your_google_drive_folder_id'

@app.route('/')
def index():
    sheets = list_files_in_folder(FOLDER_ID)
    return render_template('index.html', sheets=sheets)

@app.route('/process', methods=['POST'])
def process_sheets():
    sheet_id = request.form['sheet_id']
    data = get_sheet_data(sheet_id, 'A1:Z')  # Adjust range as needed
    filtered_data = filter_data(data)
    
    processed_data = []
    for row in filtered_data:
        name = process_name(row[0])  # Assuming name is in the first column
        personalization_data = extract_personalization_data(row)
        linkedin_data = get_linkedin_data(row[1])  # Assuming LinkedIn URL is in the second column
        search_results = search_google(f"{name} {row[2]} interview OR podcast OR guest")  # Assuming company is in the third column
        
        processed_row = {
            'name': name,
            'personalization_data': personalization_data,
            'linkedin_data': linkedin_data,
            'search_results': search_results
        }
        processed_data.append(processed_row)
    
    return jsonify(processed_data)

@app.route('/save', methods=['POST'])
def save_data():
    sheet_id = request.form['sheet_id']
    data = request.json['data']
    result = update_sheet_data(sheet_id, 'A1:Z', data)  # Adjust range as needed
    return jsonify({'success': True, 'updated_cells': result.get('updatedCells')})