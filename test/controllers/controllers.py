# controllers/main.py
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError:
    _logger.warning("gspread or oauth2client not installed. Google Sheets export will not work.")
    gspread = None

from datetime import datetime
import tempfile
import os


class GoogleSheetsExportController(http.Controller):

    def _get_google_client(self):
        """Initialize Google Sheets client"""
        if not gspread:
            raise Exception("gspread library not installed. Please install: pip3 install gspread oauth2client")

        try:
            ICP = request.env['ir.config_parameter'].sudo()
            credentials_json = ICP.get_param('google_sheets.credentials_json')

            if not credentials_json:
                raise Exception(
                    "Google credentials not configured. Add 'google_sheets.credentials_json' in System Parameters")

            # Create temp file for credentials
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                f.write(credentials_json)
                credentials_path = f.name

            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/spreadsheets'
            ]

            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
            client = gspread.authorize(creds)

            # Cleanup
            if os.path.exists(credentials_path):
                os.unlink(credentials_path)

            return client
        except Exception as e:
            _logger.error(f"Google auth failed: {str(e)}")
            raise

    def _format_value(self, value):
        """Format field value for Google Sheets"""
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        elif hasattr(value, 'name'):  # Many2one
            return value.name or ''
        elif isinstance(value, (list, tuple)):  # Many2many, One2many
            return ', '.join([str(v.name) if hasattr(v, 'name') else str(v) for v in value])
        elif isinstance(value, bool):
            return 'Yes' if value else 'No'
        elif value is False or value is None:
            return ''
        return str(value)

    def _get_field_value(self, record, field_path):
        """Get field value with support for relational fields"""
        try:
            if '/' in field_path:
                value = record
                for field in field_path.split('/'):
                    if not value:
                        return ''
                    value = getattr(value, field, '')
                return value
            return getattr(record, field_path, '')
        except:
            return ''

    @http.route('/web/export/google_sheets', type='json', auth='user')
    def export_to_google_sheets(self, model, fields, field_labels=None, ids=None, domain=None, context=None, **kwargs):
        """Export SELECTED records to Google Sheets - Clears existing data first"""
        try:
            _logger.info("=" * 70)
            _logger.info("GOOGLE SHEETS EXPORT STARTED")
            _logger.info(f"Model: {model}")
            _logger.info(f"Fields: {fields}")
            _logger.info(f"Selected IDs: {ids}")
            # Get spreadsheet ID from config
            ICP = request.env['ir.config_parameter'].sudo()
            spreadsheet_id = ICP.get_param('google_sheets.spreadsheet_id')
            print(fields)
            print(model)
            print(ids)
            if not spreadsheet_id:
                return {
                    'success': False,
                    'error': 'Spreadsheet ID not configured. Add "google_sheets.spreadsheet_id" in System Parameters'
                }

            # Fetch ONLY selected records
            Model = request.env[model].with_context(context or {})

            if ids:
                # Use selected IDs
                records = Model.browse(ids)
                _logger.info(f"Exporting {len(ids)} selected records")
            elif domain:
                # Fallback to domain if no IDs provided
                records = Model.search(domain)
                _logger.info(f"Exporting records matching domain")
            else:
                return {'success': False, 'error': 'No records selected'}

            _logger.info(f"Found {len(records)} records to export")

            if not records:
                return {'success': False, 'error': 'No records to export'}

            # Prepare data
            export_data = []
            headers = field_labels if field_labels else fields
            export_data.append(headers)

            # Add rows
            for record in records:
                row = []
                for field_path in fields:
                    value = self._get_field_value(record, field_path)
                    formatted = self._format_value(value)
                    row.append(formatted)
                export_data.append(row)

            _logger.info(f"Prepared {len(export_data)} rows (including header)")

            # Connect to Google Sheets
            client = self._get_google_client()
            spreadsheet = client.open_by_key(spreadsheet_id)

            # ALWAYS USE THE FIRST SHEET (index 0)
            worksheet = spreadsheet.get_worksheet(0)

            if not worksheet:
                return {'success': False, 'error': 'Could not access the first worksheet'}

            _logger.info(f"Using worksheet: {worksheet.title}")

            # # ✅ CLEAR ALL EXISTING DATA FIRST
            worksheet.clear()
            _logger.info("✅ Cleared all existing data from worksheet")
            #
            # # ✅ Write new data starting from A1
            worksheet.update(export_data, 'A1', value_input_option='USER_ENTERED')
            _logger.info(f"✅ Wrote {len(export_data)} rows to worksheet")

            # Format header row (row 1)
            # header_range = f'A1:{chr(64 + len(headers))}1' if len(headers) <= 26 else f'A1:Z1'
            # worksheet.format(header_range, {
            #     'textFormat': {'bold': True, 'fontSize': 11},
            #     'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.86},
            #     'horizontalAlignment': 'CENTER'
            # })

            # Freeze header row
            worksheet.freeze(rows=1)

            # Auto-resize columns
            try:
                worksheet.columns_auto_resize(0, len(headers) - 1)
            except:
                pass  # Some gspread versions don't support this

            _logger.info(f"✅ Export successful: {spreadsheet.url}")
            _logger.info("=" * 70)

            return {
                'success': True,
                'spreadsheet_url': spreadsheet.url,
                'worksheet_title': worksheet.title,
                'records_count': len(records),
                'message': f'Successfully exported {len(records)} records to "{worksheet.title}"!'
            }

        except Exception as e:
            _logger.error(f"❌ Export failed: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}