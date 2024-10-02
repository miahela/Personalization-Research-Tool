import asyncio
from threading import Event

from flask import render_template, request, jsonify, Response, stream_with_context, current_app
from app import app
from app.services.stream_processed_spreadsheet_service import stream_processed_spreadsheets, ensure_bytes
from app.services.sheet_listing_service import get_all_spreadsheets_in_drive, update_sheet_data
from app.services.spreadsheet_save_data import save_entry
from flask_sse import sse
import time


@app.route('/')
def index():
    start_time = time.time()
    sheets = get_all_spreadsheets_in_drive()
    print("--- Get All Spreadsheets in Drive in %s seconds ---" % (time.time() - start_time))
    return render_template('index.html', sheets=sheets)


continue_event = Event()


@app.route('/process_stream', methods=['GET'])
def process_sheets_stream():
    spreadsheet_ids = request.args.getlist('sheet_id')
    small_batch_size = int(request.args.get('small_batch_size', 2))
    large_batch_size = int(request.args.get('large_batch_size', 10))

    if not spreadsheet_ids:
        return jsonify({"error": "No spreadsheet IDs provided"}), 400

    def generate():
        stream = stream_processed_spreadsheets(spreadsheet_ids, continue_event, small_batch_size, large_batch_size)
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
    result = save_entry(data)
    return jsonify(result)
