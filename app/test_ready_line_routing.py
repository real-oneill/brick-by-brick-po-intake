import unittest

import pandas as pd

from logic import ready_order_lines, review_status


class ReadyLineRoutingTests(unittest.TestCase):
    def setUp(self):
        self.lines = pd.DataFrame({
            'source_doc_id': ['DOC-1', 'DOC-1', 'DOC-2'],
            'po_number': ['PO-1', 'PO-1', 'PO-2'],
            'source_order_index': [0, 0, 0],
            'quality_status': ['READY', 'REVIEW', 'READY'],
            'needs_review': [False, True, False],
        })

    def test_ready_line_routes_even_when_order_is_mixed(self):
        routed = ready_order_lines(self.lines, pd.DataFrame())
        self.assertEqual(routed.index.tolist(), [0, 2])

    def test_auto_line_does_not_hide_mixed_order(self):
        orders = pd.DataFrame({
            'source_doc_id': ['DOC-1', 'DOC-2'],
            'po_number': ['PO-1', 'PO-2'],
            'source_order_index': [0, 0],
            'status': ['REVIEW', 'READY'],
        })
        approved = pd.DataFrame({
            'source_doc_id': ['DOC-1', 'DOC-2'],
            'po_number': ['PO-1', 'PO-2'],
            'source_order_index': [0, 0],
            'approval_type': ['AUTO', 'AUTO'],
        })
        statuses = review_status(orders, approved, pd.DataFrame())
        self.assertEqual(statuses.tolist(), ['Pending', 'Approved'])


if __name__ == '__main__':
    unittest.main()
