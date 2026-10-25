"""Restricted, deterministic tools for the bookstore assistant.
No arbitrary Python or SQL from the model is executed.
"""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent
CHAT_DIR = ROOT / 'chat_data'
DASH_DIR = ROOT / 'dashboard_data'

TABLE_COLUMNS = {
    'orders': ['order_id', 'user_id', 'real_user_id', 'book_id', 'date', 'quantity', 'paid_price'],
    'books': ['book_id', 'title', 'authors', 'genre', 'publisher', 'year'],
    'users': ['user_id', 'real_user_id', 'email_initial', 'email_domain'],
}
NUMERIC = {'quantity', 'paid_price', 'book_id', 'order_id', 'user_id', 'real_user_id', 'year'}
OPS = {'eq', 'neq', 'contains', 'starts_with', 'in', 'gte', 'lte', 'between'}


def _store(store):
    s = str(store).upper()
    if s not in {f'STORE{i}' for i in range(1, 6)}:
        raise ValueError('Store must be STORE1, STORE2, STORE3, STORE4 or STORE5')
    return s.lower()


def get_schema(store):
    """Discover available queryable tables/columns."""
    s = _store(store)
    return {
        'store': s.upper(),
        'tables': TABLE_COLUMNS,
        'filters': sorted(OPS),
        'note': 'Users data has no full names, addresses, phone numbers or email addresses. '
                'Only email_initial and email_domain are available. '
                'Books and orders may be joined for title/author and customer analyses. '
                'For real distinct users use real_user_id. '
                'Author sets are stored as an entire comma-separated authors string.',
    }


def _load(store, table):
    s = _store(store)
    if table not in TABLE_COLUMNS:
        raise ValueError('Unknown table')
    path = CHAT_DIR / f'{s}_{table}.csv'
    if not path.is_file():
        raise FileNotFoundError(f'Missing {path.name}; run the export cell in its notebook')
    df = pd.read_csv(path)
    if len(df) > 200_000:
        raise ValueError('Dataset is too large for this app')
    return df


def _join(store, table):
    if table == 'orders_books':
        orders = _load(store, 'orders')
        books = _load(store, 'books')
        return orders.merge(books, on='book_id', how='left', validate='many_to_one')
    if table == 'orders_users':
        orders = _load(store, 'orders')
        users = _load(store, 'users').drop_duplicates('user_id')
        return orders.merge(users.drop(columns=['real_user_id'], errors='ignore'), on='user_id', how='left', validate='many_to_one')
    return _load(store, table)


def query_data(store, table, filters=None, metric='count_rows', column=None, group_by=None, limit=10):
    """Perform exact counts, sums, averages and safe aggregate breakdowns.

    Supported tables: orders, books, users, orders_books, orders_users.
    Metrics: count_rows, count_distinct, sum, mean, min, max.
    Filters: [{"column":"date", "op":"between", "value":["2025-01-01","2025-12-31"]}]
    """
    if table not in (*TABLE_COLUMNS, 'orders_books', 'orders_users'):
        raise ValueError('Invalid table')
    df = _join(store, table)
    filters = filters or []
    if len(filters) > 10:
        raise ValueError('Too many filters')
    for flt in filters:
        name, op, value = flt.get('column'), flt.get('op'), flt.get('value')
        if name not in df.columns or op not in OPS:
            raise ValueError(f'Invalid filter {name}/{op}; columns available: {list(df.columns)}')
        series = df[name]
        if op in {'contains', 'starts_with'}:
            if not isinstance(value, str) or len(value) > 100:
                raise ValueError('Text filter must be a string of at most 100 chars')
            vals = series.fillna('').astype(str)
            keep = vals.str.contains(value, case=False, regex=False) if op == 'contains' else vals.str.lower().str.startswith(value.lower())
        elif op == 'in':
            if not isinstance(value, list) or len(value) > 30:
                raise ValueError('The in filter needs a list of at most 30 values')
            keep = series.astype(str).isin([str(v) for v in value])
        elif op == 'between':
            if not isinstance(value, list) or len(value) != 2:
                raise ValueError('between needs [lower, upper]')
            if name in NUMERIC:
                keep = pd.to_numeric(series, errors='coerce').between(float(value[0]), float(value[1]))
            else:
                keep = series.astype(str).between(str(value[0]), str(value[1]))
        elif op in {'gte', 'lte'}:
            if name in NUMERIC:
                a, b = pd.to_numeric(series, errors='coerce'), float(value)
            else:
                a, b = series.astype(str), str(value)
            keep = a >= b if op == 'gte' else a <= b
        else:
            keep = series.astype(str) == str(value)
            if op == 'neq':
                keep = ~keep
        df = df[keep.fillna(False)]

    if column is not None and column not in df.columns:
        raise ValueError(f'Unknown column {column}; available: {list(df.columns)}')
    if group_by is not None and group_by not in df.columns:
        raise ValueError(f'Unknown group_by {group_by}; available: {list(df.columns)}')
    if metric not in {'count_rows', 'count_distinct', 'sum', 'mean', 'min', 'max'}:
        raise ValueError('Invalid metric')
    if metric != 'count_rows' and column is None:
        raise ValueError('column is required for this metric')
    if metric in {'sum', 'mean', 'min', 'max'} and column not in NUMERIC:
        raise ValueError('Numeric column required')
    limit = max(1, min(30, int(limit)))

    def measure(part):
        if metric == 'count_rows':
            return int(len(part))
        if metric == 'count_distinct':
            return int(part[column].nunique())
        nums = pd.to_numeric(part[column], errors='coerce')
        result = {'sum': nums.sum, 'mean': nums.mean, 'min': nums.min, 'max': nums.max}[metric]()
        return round(float(result), 4) if pd.notna(result) else None

    answer = {'store': _store(store).upper(), 'table': table, 'matched_rows': len(df), 'metric': metric, 'column': column, 'group_by': group_by}
    if group_by:
        vals = [{'group': str(key), 'value': measure(part)} for key, part in df.groupby(group_by, dropna=False)]
        vals.sort(key=lambda x: (x['value'] is not None, x['value'] if x['value'] is not None else float('-inf')), reverse=True)
        answer['groups'] = vals[:limit]
        answer['total_groups'] = len(vals)
    else:
        answer['value'] = measure(df)
    return answer


def dashboard_summary(store):
    path = DASH_DIR / f'{_store(store)}.json'
    if not path.is_file():
        raise FileNotFoundError(f'Missing dashboard JSON for {store}')
    with path.open(encoding='utf-8') as f:
        data = json.load(f)
    return {'store': _store(store).upper(), 'unique_users': data.get('unique_users'),
            'author_sets': data.get('author_sets'), 'most_popular_authors': data.get('most_popular_authors'),
            'best_buyer_ids': data.get('best_buyer_ids'), 'top_5_days': data.get('top_5_days'),
            'total_revenue': round(sum(float(d['revenue']) for d in data.get('daily_revenue', [])), 2)}

TOOLS = [
    {'type': 'function', 'function': {'name': 'get_schema', 'description': 'Get available data tables, columns and filter operators for a store. Use first for unfamiliar questions.', 'parameters': {'type':'object','properties':{'store':{'type':'string'}},'required':['store']}}},
    {'type': 'function', 'function': {'name': 'dashboard_summary', 'description': 'Retrieve validated precomputed dashboard results: reconciled users, author sets, best buyer, top 5 revenue days and totals.', 'parameters': {'type':'object','properties':{'store':{'type':'string'}},'required':['store']}}},
    {'type': 'function', 'function': {'name': 'query_data', 'description': 'Execute deterministic filtering and exact aggregations over sanitized data. Tables: orders, users, books, orders_books, orders_users. Filter fields: column, op, value. Supported metrics count_rows, count_distinct, sum, mean, min, max. Call get_schema first to learn columns.', 'parameters': {'type':'object','properties':{
        'store':{'type':'string'}, 'table':{'type':'string'}, 'filters':{'type':'array','items':{'type':'object','properties':{'column':{'type':'string'},'op':{'type':'string'},'value':{}},'required':['column','op','value']}},
        'metric':{'type':'string'},'column':{'type':['string','null']}, 'group_by':{'type':['string','null']},'limit':{'type':'integer'}}, 'required':['store','table']}}}
]

CALLS = {'get_schema': get_schema, 'dashboard_summary': dashboard_summary, 'query_data': query_data}
