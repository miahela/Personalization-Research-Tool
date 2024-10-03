from threading import Event

from flask import render_template, request, jsonify, Response, stream_with_context

from app import app
from app.services.spreadsheet_service import SpreadsheetService
from app.services.process_and_stream_contacts import process_and_stream_contacts
from app.utils.file_manager import get_file_manager


@app.route('/')
def index():
    spreadsheets = SpreadsheetService.get_instance().get_all_spreadsheets_in_drive()
    spreadsheets_response = []
    for spreadsheet in spreadsheets:
        calculated_spreadsheet = {
            'id': spreadsheet.id,
            'name': spreadsheet.name,
            'empty_by_the_way_count': len(SpreadsheetService.get_instance().calculate_unprocessed_rows_in_sheet(
                spreadsheet.new_connections))
        }
        spreadsheets_response.append(calculated_spreadsheet)
    return render_template('index.html', sheets=spreadsheets_response)


continue_event = Event()


@app.route('/process_stream', methods=['GET'])
def process_sheets_stream():
    spreadsheet_ids = request.args.getlist('sheet_id')
    small_batch_size = int(request.args.get('small_batch_size', 2))
    large_batch_size = int(request.args.get('large_batch_size', 10))

    if not spreadsheet_ids:
        return jsonify({"error": "No spreadsheet IDs provided"}), 400

    def generate():
        stream = process_and_stream_contacts(spreadsheet_ids, continue_event, small_batch_size, large_batch_size)
        for item in stream:
            yield item

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/continue_processing', methods=['POST'])
def continue_processing():
    continue_event.set()
    return jsonify({"status": "processing continued"})


@app.route('/stop_processing', methods=['POST'])
def stop_processing():
    continue_event.clear()
    return jsonify({"status": "processing stopped"})


@app.route('/save', methods=['POST'])
def save_data():
    data = request.json
    spreadsheet_id = data.get('sheet_id')
    row_number = data.get('row_number')
    entry_data = data.get('entry_data')
    username = data.get('username')
    result = SpreadsheetService.get_instance().update_row(spreadsheet_id, "New Connections", row_number, entry_data)

    file_manager = get_file_manager()
    file_manager.delete_all_files_by_user(username)
    return jsonify(result)
