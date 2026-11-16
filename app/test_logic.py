import unittest

import pandas as pd

from logic import demo_cases, portfolio_metrics, recommended_actions


class PortfolioMetricsTests(unittest.TestCase):
    def test_dashboard_aligned_metrics(self):
        lines = pd.DataFrame({
            'po_number': ['PO-1', 'PO-1', 'PO-2', None, ''],
            'quality_status': ['READY', 'READY', 'REVIEW', 'FAILED', 'READY'],
        })
        self.assertEqual(portfolio_metrics(lines), {
            'purchase_orders': 2,
            'total_lines': 5,
            'ready_lines': 3,
            'review_lines': 1,
            'failed_lines': 1,
            'ready_line_share': 0.6,
        })


class RecommendedActionsTests(unittest.TestCase):
    def test_actions_follow_review_reasons(self):
        actions = recommended_actions([
            'Ship-to unresolved; SKU unresolved; Document price differs from contract price'
        ], 'REVIEW')
        self.assertTrue(any('delivery location' in action for action in actions))
        self.assertTrue(any('product or SKU' in action for action in actions))
        self.assertTrue(any('document and contract prices' in action for action in actions))

    def test_failed_fallback(self):
        self.assertEqual(len(recommended_actions([], 'FAILED')), 1)


class DemoCasesTests(unittest.TestCase):
    def test_one_candidate_per_available_status(self):
        orders = pd.DataFrame({
            'status': ['READY', 'REVIEW', 'FAILED'],
            'confidence': [0.99, 0.7, 0.2],
            'lines': [2, 3, 1],
            'known_value': [100, 500, None],
            'source_doc_id': ['DOC-R', 'DOC-V', 'DOC-F'],
            'po_number': ['PO-R', 'PO-V', None],
            'channel': ['erp_edi', 'email_pdf', 'handwritten'],
        })
        picks = demo_cases(orders)
        self.assertEqual(set(picks['Workflow']), {'READY', 'REVIEW', 'FAILED'})
        self.assertEqual(set(picks['Document']), {'DOC-R', 'DOC-V', 'DOC-F'})


if __name__ == '__main__':
    unittest.main()
