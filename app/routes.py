from flask import render_template, request, jsonify, Response, stream_with_context, current_app
from app import app
from app.services.stream_processed_spreadsheet_service import stream_processed_spreadsheets
from app.services.sheet_listing_service import get_all_spreadsheets_in_drive, update_sheet_data
from app.services.spreadsheet_save_data import save_entry
import time


@app.route('/')
def index():
    start_time = time.time()
    sheets = get_all_spreadsheets_in_drive()
    print("--- Get All Spreadsheets in Drive in %s seconds ---" % (time.time() - start_time))
    return render_template('index.html', sheets=sheets)


@app.route('/process_stream', methods=['GET'])
def process_sheets_stream():
    spreadsheet_ids = request.args.getlist('sheet_id')

    if not spreadsheet_ids:
        return jsonify({"error": "No spreadsheet IDs provided"}), 400

    return Response(stream_with_context(stream_processed_spreadsheets(spreadsheet_ids)), mimetype='text/event-stream')


@app.route('/save', methods=['POST'])
def save_data():
    data = request.json
    result = save_entry(data)
    return jsonify(result)
