# 2 · Create your first app (Free Edition)

> The hackathon requires demoing on **Databricks Free Edition** — sign up at [databricks.com/learn/free-edition](https://www.databricks.com/learn/free-edition). Do **not** use a paid/enterprise workspace for the submission.

## Fastest route: start from a template in the UI

1. In your workspace, open the app switcher (top-left grid icon) → **Databricks Apps**.
2. Click **Create app**.
3. Pick a template — e.g. **Streamlit Hello World** (Gradio/Dash/Flask templates also exist).
4. Name it (e.g. `medical-desert-planner`) and click **Create app**.
5. Databricks provisions serverless compute, deploys the template, and gives you a public app URL. Click it to see the running app.

The template's source lands in your workspace under `/Workspace/Users/<you>/databricks_apps/<app-name>/`. You can edit it right in the workspace editor and hit **Deploy** to redeploy.

## Pull the template code to your laptop

Once the template app exists, export it and work locally (see [guide 3](03-develop-and-deploy.md) for the full loop):

```bash
databricks workspace export-dir \
  "/Workspace/Users/<you>/databricks_apps/<app-name>" ./my-app
```

## Creating an app from the CLI instead

```bash
databricks apps create medical-desert-planner
```

This creates the app shell (compute + URL + service principal) with no code yet; you attach code with a deploy (guide 3).

## What you get per app

- A **URL** (`https://<app-name>-<id>.aws.databricksapps.com`) — authenticated to your workspace users by default.
- A **service principal** identity the app runs as — grant it access to any tables/warehouses the app queries.
- An **Overview page** in the UI with status, the exact deploy command for your app, an **Environment** tab (env vars), and a **Logs** tab (stdout/stderr — your first stop when something breaks).

Next: [3 · Local development & deployment](03-develop-and-deploy.md)
