"""Portfolio metrics are computed from Gold, never from the answer key."""
import hashlib
import pandas as pd

ORDER_KEYS = ['source_doc_id', 'po_number', 'source_order_index']

# Fields a reviewer may correct before approving. Everything else is taken as extracted.
EDITABLE_FIELDS = ['po_number', 'material_id', 'quantity_each', 'expected_net_price',
    'master_customer_name', 'master_ship_to_name']

ACTION_RULES = (
    (('missing po',), 'Enter or confirm the purchase order number from the source document.'),
    (('customer unresolved',), 'Confirm the customer and select the correct customer record.'),
    (('ship-to unresolved',), 'Confirm the delivery location and select the correct ship-to record.'),
    (('sku unresolved', 'missing item code'), 'Check the source item and select the correct product or SKU.'),
    (('contract price unavailable',), 'Confirm the applicable contract price before approval.'),
    (('price differs', 'price mismatch'), 'Compare the document and contract prices, then confirm the approved price.'),
    (('invalid or unconverted quantity',), 'Confirm the quantity and unit of measure, then correct the unit quantity.'),
    (('insufficient atp', 'partial shipment'), 'Review the proposed partial shipment and confirm the quantity to ship.'),
    (('no atp', 'backorder'), 'Confirm whether the line should be backordered or held.'),
    (('discontinued', 'successor'), 'Review the proposed successor product before approval.'),
    (('atp decision unavailable', 'line cancelled'), 'Confirm the inventory decision or cancellation with operations.'),
    (('low header confidence', 'low line confidence'), 'Compare the extracted fields with the source evidence.'),
)

# Captured in the approved-orders snapshot; also the basis for detecting Gold drift.
SNAPSHOT_FIELDS = ['source_doc_id', 'po_number', 'source_order_index', 'line_number',
    'item_code', 'item_description', 'material_id', 'master_customer_name', 'master_ship_to_name',
    'quantity_each', 'expected_net_price', 'currency', 'channel', 'proposed_atp_outcome',
    'proposed_ship_quantity', 'overall_confidence', 'quality_status']

def orders_from_lines(lines):
    work = lines.copy()
    for col in ORDER_KEYS:
        if col not in work:
            work[col] = None
    work['review_line'] = work['needs_review'].fillna(True).astype(bool)
    work['failed_line'] = work['quality_status'].eq('FAILED')
    work['line_value'] = pd.to_numeric(work['quantity_each'], errors='coerce') * pd.to_numeric(work['expected_net_price'], errors='coerce')
    work['confidence'] = pd.to_numeric(work['overall_confidence'], errors='coerce')
    work['missing_confidence'] = work['confidence'].isna()
    result = work.groupby(ORDER_KEYS, dropna=False).agg(
        customer=('master_customer_name', 'first'), channel=('channel', 'first'),
        currency=('currency', 'first'), lines=('source_doc_id', 'size'),
        confidence=('confidence', 'min'), unknown_confidence=('missing_confidence', 'any'),
        needs_review=('review_line', 'any'), failed=('failed_line', 'any'),
        known_value=('line_value', lambda x: x.sum(min_count=1)),
        priced_lines=('line_value', 'count'),
    ).reset_index()
    result.loc[result['unknown_confidence'], 'confidence'] = float('nan')
    result['status'] = result.apply(lambda r: 'FAILED' if r['failed'] else 'REVIEW' if r['needs_review'] else 'READY', axis=1)
    # Value sorting is only meaningful within a currency. No implicit FX conversion.
    return result.sort_values(['confidence', 'currency', 'known_value'], ascending=[True, True, False], na_position='first').reset_index(drop=True)


def portfolio_metrics(lines):
    """Dashboard-aligned portfolio KPIs, calculated directly from Gold lines.

    Purchase orders follow the dashboard definition: distinct, non-empty PO
    numbers. READY percentage is line based, not a percentage of review cases.
    """
    po_numbers = lines.get('po_number', pd.Series(dtype='object')).dropna().astype(str).str.strip()
    po_numbers = po_numbers[po_numbers.ne('')]
    statuses = lines.get('quality_status', pd.Series(index=lines.index, dtype='object')).fillna('')
    total_lines = len(lines)
    ready_lines = int(statuses.eq('READY').sum())
    return {
        'purchase_orders': int(po_numbers.nunique()),
        'total_lines': total_lines,
        'ready_lines': ready_lines,
        'review_lines': int(statuses.eq('REVIEW').sum()),
        'failed_lines': int(statuses.eq('FAILED').sum()),
        'ready_line_share': ready_lines / total_lines if total_lines else 0.0,
    }


def recommended_actions(review_reasons, status=None):
    """Plain-language next steps inferred from Gold's review reasons."""
    reason_text = '; '.join(str(value) for value in review_reasons if value is not None and not pd.isna(value)).lower()
    actions = []
    for needles, action in ACTION_RULES:
        if any(needle in reason_text for needle in needles) and action not in actions:
            actions.append(action)
    if not actions and status == 'FAILED':
        actions.append('Compare the extracted order with the source document and complete the missing required fields.')
    elif not actions and status == 'REVIEW':
        actions.append('Review the flagged fields against the source evidence before approval.')
    return actions


def demo_cases(orders):
    """Select one useful live example for each workflow path.

    These are suggestions from the currently loaded Gold snapshot, not
    hardcoded document IDs that can become stale after a refresh.
    """
    picks = []
    for status in ('READY', 'REVIEW', 'FAILED'):
        candidates = orders[orders.status.eq(status)].copy()
        if candidates.empty:
            continue
        if status == 'READY':
            candidates = candidates.sort_values(['confidence', 'lines'], ascending=[False, False], na_position='last')
            purpose = 'Show automatic inclusion in Approved orders.'
        elif status == 'REVIEW':
            candidates = candidates.sort_values(['known_value', 'confidence'], ascending=[False, True], na_position='last')
            purpose = 'Show review flags, suggested actions, edits and manual approval.'
        else:
            candidates = candidates.sort_values(['confidence', 'lines'], ascending=[True, False], na_position='first')
            purpose = 'Show missing critical data, source evidence, correction and manual approval.'
        row = candidates.iloc[0]
        picks.append({
            'Workflow': status,
            'Document': row.get('source_doc_id'),
            'PO number': row.get('po_number'),
            'Channel': row.get('channel'),
            'Why use it': purpose,
        })
    return pd.DataFrame(picks)

def select_order(lines, order):
    mask = pd.Series(True, index=lines.index)
    for col in ORDER_KEYS:
        value = order[col]
        mask &= lines[col].isna() if pd.isna(value) else lines[col].eq(value)
    return lines.loc[mask].copy()


def _cell(row, column):
    value = row.get(column)
    return '' if value is None or pd.isna(value) else str(value)

def row_hash(row, columns=SNAPSHOT_FIELDS):
    return hashlib.sha256('|'.join(_cell(row, c) for c in columns).encode('utf-8')).hexdigest()

def line_identifier(row):
    """A durable id for one Gold line. Falls back to a content hash when Gold
    carries no upstream line_id; the fallback is flagged because it cannot
    survive a re-extraction of the source document (see app/README.md)."""
    line_id = row.get('line_id')
    if line_id is not None and not pd.isna(line_id) and str(line_id).strip():
        return str(line_id), False
    basis = ['source_doc_id', 'po_number', 'source_order_index', 'line_number',
        'item_code', 'item_description', 'quantity_as_written']
    return hashlib.sha256('|'.join(_cell(row, c) for c in basis).encode('utf-8')).hexdigest(), True

def diff_editable_fields(original_row, edited_row):
    """Field-level before/after for the fields a reviewer is allowed to correct."""
    changes = []
    for field in EDITABLE_FIELDS:
        before, after = _cell(original_row, field), _cell(edited_row, field)
        if before != after:
            changes.append((field, before, after))
    return changes

def ready_order_lines(lines, orders):
    """Every line belonging to a READY order: the set eligible for automatic inclusion."""
    ready_keys = orders.loc[orders.status.eq('READY'), ORDER_KEYS]
    return lines.merge(ready_keys, on=ORDER_KEYS, how='inner')
