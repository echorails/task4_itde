"""Run with `%run ../export_chat_data.py` in each store notebook AFTER Run All.
Requires existing notebook variables: df_users, df_orders, df_books.
Exports data minimized for PUBLIC deployment; no full email/name/address/phone.
"""
from pathlib import Path
import pandas as pd

cwd = Path.cwd()
if not cwd.name.upper().startswith('STORE'):
    raise RuntimeError('Open and run the notebook from its STORE1..STORE5 folder first')
store = cwd.name.lower()
out = cwd.parent / 'chat_data'
out.mkdir(parents=True, exist_ok=True)

required_users={'id','real_user_id','email'}
required_orders={'user_id','real_user_id','book_id','date','quantity','paid_price'}
required_books={':id',':title',':author'}
for label, actual, required in [('users',set(df_users.columns),required_users),('orders',set(df_orders.columns),required_orders),('books',set(df_books.columns),required_books)]:
    if not required.issubset(actual):
        raise RuntimeError(f'{label}: missing {required-actual}. Run all analysis cells before export.')

users=pd.DataFrame({
    'user_id':pd.to_numeric(df_users['id'],errors='raise').astype('int64'),
    'real_user_id':pd.to_numeric(df_users['real_user_id'],errors='raise').astype('int64'),
    'email_initial':df_users['email'].fillna('').astype(str).str.lower().str[:1],
    'email_domain':df_users['email'].fillna('').astype(str).str.split('@').str[-1].str.lower(),
})
users.to_csv(out/f'{store}_users.csv',index=False)

orders=pd.DataFrame({
    'order_id':df_orders['order_id'] if 'order_id' in df_orders.columns else range(1,len(df_orders)+1),
    'user_id':df_orders['user_id'],
    'real_user_id':df_orders['real_user_id'],
    'book_id':df_orders['book_id'],
    'date':df_orders['date'].astype(str),
    'quantity':df_orders['quantity'],
    'paid_price':df_orders['paid_price'].astype(float).round(2),
})
orders.to_csv(out/f'{store}_orders.csv',index=False)

books=pd.DataFrame({
    'book_id':df_books[':id'],
    'title':df_books[':title'].fillna(''),
    'authors':df_books[':author'].fillna(''),
    'genre':df_books[':genre'] if ':genre' in df_books else '',
    'publisher':df_books[':publisher'] if ':publisher' in df_books else '',
    'year':df_books[':year'] if ':year' in df_books else pd.NA,
})
books.to_csv(out/f'{store}_books.csv',index=False)
print('Exported:',store, '- orders:',len(orders),'users:',len(users),'books:',len(books))
print('Location:',out)
