# Part 2 setup — bookstore AI dashboard

1. Put `app.py`, `chat_tools.py`, `export_chat_data.py`, `requirements.txt` in the **root** of your existing `task4` repository (replace old `app.py`). Keep `dashboard_data/store1.json` ... `store5.json`.
2. Open each STORE notebook. Make sure you have **restarted and run all cells**, including corrected currency conversion, and are running it from the matching STORE directory.
3. At the end of each notebook add a cell:
   ```python
   %run -i ../export_chat_data.py
   ```
   Run the cell. This creates 15 files under `chat_data/` (3 per store). The export excludes real full names, full emails, addresses and phone numbers. It does contain user IDs, metadata, books and order amounts; check whether public release of this data is permitted.
4. To try locally, install: `python -m pip install -r requirements.txt`
5. Create `.streamlit/secrets.toml` locally **DO NOT UPLOAD THIS FILE**:
   ```toml
   OPENAI_API_KEY = "your_actual_api_key"
   OPENAI_MODEL = "gpt-4.1-mini"
   ```
   The OpenAI API is separately billed, even if you pay for ChatGPT. Choose a model that supports tool calling; check prices and supported models in your account.
6. Add to `.gitignore`: `.streamlit/secrets.toml`, `.env`, `STORE*/users.csv`, `STORE*/orders.parquet`, `STORE*/books.yaml`, `*.zip`.
7. Run `python -m streamlit run app.py`, check STORE1–STORE5, then open the AI Assistant tab. Try questions:
   - How many real unique users in STORE1?
   - How many books were sold between 2025-08-01 and 2025-08-31?
   - How many user records have an email starting with s? And with p?
   - Which author set sold most copies?
8. Upload `app.py`, `chat_tools.py`, `export_chat_data.py`, `requirements.txt`, `chat_data/*.csv`, `dashboard_data/*.json` and your cleaned notebooks to GitHub.
9. In Streamlit Community Cloud → Manage App → Settings → Secrets, enter the same `OPENAI_API_KEY` and `OPENAI_MODEL` values from step 5. Save, reboot app if necessary.
10. Test the public app in an incognito window before submission. Inspect tool responses and compare with notebook outputs, especially on questions about dates and real users. **The chat requires an API key and internet connection**.

## Limits
- The assistant cannot access users' full names, full email addresses, addresses or phones by design. It can use email initials and domains. This is deliberate data minimization.
- No free-text modifications of the dashboard (Part 3); the optional third part is not implemented.
- Without an API key the dashboard's analytical tabs still work but AI answers do not.
- A public demo exposes summarized/derived records that you choose to publish. Do not publish without permission.
- Group-by `authors` treats each comma-separated string as a full author set. Questions about individual co-authors require additional logic.
