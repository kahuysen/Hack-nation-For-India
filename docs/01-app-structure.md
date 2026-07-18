# 1 · What a Databricks App is made of

A Databricks App is just a folder of files that Databricks runs as a web server on serverless compute. The minimum project looks like this:

```
my-app/
├── app.py            # your app code (Streamlit, Dash, Gradio, Flask, FastAPI…)
├── app.yaml          # how Databricks should run it (optional but recommended)
└── requirements.txt  # Python dependencies
```

## app.py

The code implementing the app's functionality and UI. Any Python web framework works; Databricks provides templates for **Streamlit, Dash, Gradio, and Flask/FastAPI**. For a data app like ours, Streamlit is the fastest path.

Minimal Streamlit example:

```python
import streamlit as st
import pandas as pd

st.set_page_config(page_title="My App", layout="wide")
st.title("Hello Databricks Apps")

df = pd.DataFrame({"region": ["Jaipur", "Patna"], "facilities": [42, 17]})
st.dataframe(df)
```

## app.yaml

Defines the app's entry point and environment. If you omit it, Databricks runs the first `.py` file it finds with `python <file>.py` (Node.js apps get `npm run start`) — for Streamlit you **must** specify the command:

```yaml
command: ['streamlit', 'run', 'app.py']
env:
  - name: 'STREAMLIT_GATHER_USAGE_STATS'
    value: 'false'
  - name: 'DATABRICKS_WAREHOUSE_ID'
    value: '<your-sql-warehouse-id>'
```

Notes:

- The command is **not run in a shell** — shell env vars aren't available. `DATABRICKS_APP_PORT` is substituted at runtime; your server must listen on it (Streamlit templates handle this).
- `env` entries take either a hardcoded `value` or `valueFrom` to reference a secret/resource.
- Example for a Flask app behind gunicorn:

  ```yaml
  command: [gunicorn, 'app:app', '-w', '4']
  ```

## requirements.txt

Standard pip requirements, installed when the app deploys. Pin versions so the deployed app matches what you tested locally:

```
streamlit==1.41.1
pandas==2.2.3
databricks-sql-connector==3.7.0
```

Next: [2 · Create your first app](02-create-first-app.md)
