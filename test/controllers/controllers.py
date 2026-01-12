# controllers/main.py (TEST VERSION)
from odoo import http
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)


class GoogleSheetsExportController(http.Controller):

    @http.route('/web/export/google_sheets', type='json', auth='user')
    def export_to_google_sheets(self, model, fields, field_labels, **kwargs):
        try:
            # For testing: just log the data
            _logger.info("=" * 50)
            _logger.info("GOOGLE SHEETS EXPORT TRIGGERED")
            _logger.info(f"Model: {model}")
            _logger.info(f"Fields: {fields}")
            _logger.info(f"Labels: {field_labels}")
            _logger.info("=" * 50)

            return {
                'success': True,
                'spreadsheet_url': 'https://docs.google.com/spreadsheets/d/1T04KsatWb8ptAR65UOfdTx3s8QCRLTq1jA3A69uy4Kk/edit',
                'message': 'Export triggered! Check Odoo logs for data.'
            }
        except Exception as e:
            _logger.error(f"Export error: {str(e)}")
            return {'success': False, 'error': str(e)}