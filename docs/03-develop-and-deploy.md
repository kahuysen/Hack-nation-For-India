# 3 · Local development & deployment

## One-time setup

Install the Databricks CLI (v0.229+) and authenticate:

```bash
brew install databricks   # or: curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
databricks auth login --host https://<your-workspace>.cloud.databricks.com
```

## The dev loop

### 1. Run locally

Run FastAPI from the repository root:

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Or use the CLI's local runner, which mimics the app runtime (reads `app.yaml`, injects env):

```bash
databricks apps run-local --prepare-environment --debug
```

### 2. Push through GitHub

GitHub is the source of truth for the four-person team. Work on a short-lived
branch and use a pull request:

```bash
git switch -c feature/<short-name>
git pull --rebase origin main
git push -u origin feature/<short-name>
```

Do not edit the shared Databricks Git folder or use `databricks sync` as the team
workflow. After review, merge the pull request to `main`.

### 3. Deploy the merged Git commit

```bash
databricks apps deploy <app-name> \
  --json '{"git_source": {"branch": "main"}}'
```

Configure the app's Git repository once before the first Git deployment:

```bash
databricks apps create-update <app-name> --json '{
  "update_mask": "git_repository",
  "git_repository": {
    "url": "https://github.com/kahuysen/Hack-nation-For-India",
    "provider": "gitHub"
  }
}'
```

The repository is public, so a service-principal Git credential is not needed.
For a private repository, configure that credential in the app settings.

### 4. Debug

- **Logs tab** on the app page: stdout/stderr from your process (import errors, tracebacks).
- App won't start? Check that `app.yaml`'s `command` is right and every import is in `requirements.txt`.

You can pin `"tag": "v1.0.0"` or `"commit": "<sha>"` instead of a branch. For private repos, the app's service principal needs a git credential (`databricks git-credentials create …`).

## Hackathon advice

Deploy a hello-world **on day one**. Deployment friction is the classic hackathon killer, and "works reliably in a live demo on Free Edition" is 25% of the score. Keep `main` deployable and deploy from GitHub after each reviewed merge.

Next: [4 · Connecting data & persistence](04-data-and-persistence.md)
