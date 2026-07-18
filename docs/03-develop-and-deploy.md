# 3 · Local development & deployment

## One-time setup

Install the Databricks CLI (v0.229+) and authenticate:

```bash
brew install databricks   # or: curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
databricks auth login --host https://<your-workspace>.cloud.databricks.com
```

## The dev loop

### 1. Run locally

Plain framework run works fine:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Or use the CLI's local runner, which mimics the app runtime (reads `app.yaml`, injects env):

```bash
databricks apps run-local --prepare-environment --debug
```

### 2. Sync your code to the workspace

From the project folder:

```bash
databricks sync --watch . /Workspace/Users/<you>/databricks_apps/<app-name>
```

`--watch` keeps uploading as you save files. Files matched by `.gitignore` are excluded — keep `.venv/`, `__pycache__/` etc. in there.

### 3. Deploy

```bash
databricks apps deploy <app-name> \
  --source-code-path /Workspace/Users/<you>/databricks_apps/<app-name>
```

Tip: the app's **Overview page** shows this exact command pre-filled for your app. Deploys take ~30s; the app restarts with the new code.

### 4. Debug

- **Logs tab** on the app page: stdout/stderr from your process (import errors, tracebacks).
- App won't start? Check that `app.yaml`'s `command` is right and every import is in `requirements.txt`.

## Alternative: deploy straight from GitHub

Attach this repo to the app, then deploy a branch:

```bash
databricks apps create-update <app-name> --json '{
  "update_mask": "git_repository",
  "git_repository": {"url": "https://github.com/kahuysen/Hack-nation-For-India", "provider": "gitHub"}
}'

databricks apps deploy <app-name> --json '{"git_source": {"branch": "main"}}'
```

You can pin `"tag": "v1.0.0"` or `"commit": "<sha>"` instead of a branch. For private repos, the app's service principal needs a git credential (`databricks git-credentials create …`).

## Hackathon advice

Deploy a hello-world **on day one**. Deployment friction is the classic hackathon killer, and "works reliably in a live demo on Free Edition" is 25% of the score. Once the pipeline works, `sync` + `deploy` after every meaningful change so the deployed app never drifts far from local.

Next: [4 · Connecting data & persistence](04-data-and-persistence.md)
