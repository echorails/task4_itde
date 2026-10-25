"""Task 4 bookstore dashboard, adapted from Cameron Jones's Streamlit Sales Dashboard layout."""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from chat_tools import TOOLS, CALLS

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'dashboard_data'
STORES = [f'STORE{i}' for i in range(1, 6)]


def set_page_config():
    st.set_page_config(page_title='Bookstore Sales Dashboard', page_icon='📚', layout='wide', initial_sidebar_state='expanded')
    st.markdown('<style>footer {visibility: hidden;}</style>', unsafe_allow_html=True)


@st.cache_data
def load_data(store):
    path = DATA_DIR / f'{store.lower()}.json'
    if not path.is_file():
        return None
    with path.open(encoding='utf-8') as f:
        return json.load(f)


def display_kpi_metrics(data):
    st.header('KPI Metrics')
    daily = pd.DataFrame(data.get('daily_revenue', []))
    total = pd.to_numeric(daily.get('revenue', pd.Series(dtype=float)), errors='coerce').sum()
    cols = st.columns(3)
    cols[0].metric('Total Revenue', f'${total:,.2f}')
    cols[1].metric('Unique Users', f"{data['unique_users']:,}")
    cols[2].metric('Unique Author Sets', f"{data['author_sets']:,}")


def display_charts(data):
    daily = pd.DataFrame(data.get('daily_revenue', []))
    if daily.empty or not {'date', 'revenue'}.issubset(daily.columns):
        st.warning('No daily revenue available for this store.')
        return
    daily['date'] = pd.to_datetime(daily['date'])
    daily['revenue'] = pd.to_numeric(daily['revenue'])
    daily = daily.sort_values('date')
    fig = px.line(daily, x='date', y='revenue', title='Daily Revenue', labels={'date':'Date','revenue':'Revenue (USD)'}, template='plotly_white')
    fig.update_layout(margin=dict(l=20,r=20,t=50,b=20), hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)

    col1,col2 = st.columns(2)
    with col1:
        st.subheader('Top 5 Days by Revenue')
        top5 = pd.DataFrame(data.get('top_5_days', []))
        if top5.empty:
            top5 = daily.nlargest(5, 'revenue').copy()
        top5['date'] = pd.to_datetime(top5['date']).dt.strftime('%Y-%m-%d')
        top5['revenue'] = pd.to_numeric(top5['revenue']).map(lambda n:f'${n:,.2f}')
        st.dataframe(top5.rename(columns={'date':'Date','revenue':'Revenue (USD)'}), hide_index=True, use_container_width=True)
    with col2:
        st.subheader('Most Popular Author(s)')
        authors = data.get('most_popular_authors', [])
        st.write(', '.join(map(str, authors)) if isinstance(authors,list) else str(authors))
        st.subheader('Best Buyer — All User IDs')
        st.code(json.dumps(data.get('best_buyer_ids', [])), language='json')


def ai_answer(question, store, history):
    """Use function calling; calculations only come from Python tools."""
    from openai import OpenAI
    api_key = st.secrets.get('OPENAI_API_KEY', '')
    model = st.secrets.get('OPENAI_MODEL', 'gpt-4.1-mini')
    if not api_key:
        raise ValueError('OPENAI_API_KEY is missing in Streamlit Secrets')
    client = OpenAI(api_key=api_key, timeout=35, max_retries=1)
    instructions = (
        'You are a precise bookstore data analyst. The selected store is ' + store + '. '
        'Use provided tools for EVERY factual or numerical data question, without exception. '
        'Never guess counts, prices, authors, names, or dates. '
        'If an answer cannot be computed from available tools, say what is unavailable. '
        'User IDs are identifiers and must not be added together. '
        'Distinct real people must be counted using real_user_id, never raw user_id. '
        'For author set, interpret books.authors as the full set, not individual contributors. '
        'User email data is intentionally limited to initial and domain; do not invent actual addresses. '
        'Do not claim to modify the dashboard: part 3 controls are not implemented. '
        'You may answer in the language of the user. Keep responses concise and provide units. '
        'You must call a tool when the question is about data.'
    )
    msgs = [{'role':'system','content':instructions}]
    for item in history[-8:]:
        msgs.append({'role':item['role'],'content':item['content']})
    msgs.append({'role':'user','content':question})
    used_tool = False
    for _ in range(6):
        res = client.chat.completions.create(model=model, messages=msgs, tools=TOOLS, tool_choice='auto', temperature=0)
        msg = res.choices[0].message
        msgs.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:
            if not used_tool:
                return 'I need to check the store data before answering. Please ask your question again.'
            return msg.content or 'No answer was returned.'
        for call in msg.tool_calls:
            used_tool = True
            try:
                args = json.loads(call.function.arguments)
                # Prevent cross-store drift: all tools act on the selected store
                args['store'] = store
                result = CALLS[call.function.name](**args)
            except Exception as exc:
                result = {'error':str(exc)}
            msgs.append({'role':'tool','tool_call_id':call.id,'content':json.dumps(result,ensure_ascii=False,default=str)})
    return 'The question needed too many tool steps. Please ask a narrower question.'


def assistant_view():
    st.subheader('🤖 AI Data Assistant · Part 2')
    st.caption('Questions are answered using Python data tools, not invented statistics. Full personal information is not published.')
    store = st.selectbox('Ask about store', STORES, key='chat_store')
    st.info('Try: How many real users are in STORE1? · How many books were sold in March 2025? · How many user records have email starting with s or p?')
    key = f'chat_{store}'
    if key not in st.session_state:
        st.session_state[key] = []
    for item in st.session_state[key]:
        with st.chat_message(item['role']):
            st.write(item['content'])
    prompt = st.chat_input('Ask a question about store data...', key='question_input')
    if prompt:
        history = st.session_state[key]
        with st.chat_message('user'):
            st.write(prompt)
        with st.chat_message('assistant'):
            with st.spinner('Checking the data...'):
                try:
                    answer = ai_answer(prompt,store,history)
                except Exception as exc:
                    answer = f'Assistant unavailable: {exc}'
                st.write(answer)
        history.extend([{'role':'user','content':prompt},{'role':'assistant','content':answer}])


def main():
    set_page_config()
    st.title('📚 Bookstore Sales Dashboard')
    st.caption('Task 4 · Data Engineering · Five stores')
    st.sidebar.header('Stores')
    st.sidebar.caption('Choose a store tab or use AI Assistant')
    st.sidebar.info("Layout adapted from Cameron Jones's Streamlit Sales Dashboard")
    tabs = st.tabs([*STORES, '🤖 AI Assistant'])
    for i,tab in enumerate(tabs[:5],start=1):
        with tab:
            store=f'store{i}'
            data=load_data(store)
            if data is None:
                st.warning(f'Missing dashboard_data/{store}.json. Export notebook results first.')
                continue
            display_kpi_metrics(data)
            display_charts(data)
    with tabs[5]:
        assistant_view()

if __name__ == '__main__':
    main()
