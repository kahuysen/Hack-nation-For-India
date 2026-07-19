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

### 3. Pull the merged commit into Databricks and deploy

```bash
databricks repos update <git-folder-id-or-path> --branch main
databricks apps deploy hacknation-for-india \
  --source-code-path /Workspace/Users/<you>/Hack-nation-For-India-git
```

Create the Databricks Git folder once before the first deployment:

```bash
databricks repos create \
  https://github.com/kahuysen/Hack-nation-For-India.git \
  gitHub \
  --path /Users/<you>/Hack-nation-For-India-git
```

The repository is public, so a Git credential is not needed. For a private
repository, configure a Databricks Git credential first. The App deploy source
must be this Git folder, not the older manually uploaded Workspace folder.

### 4. Debug

- **Logs tab** on the app page: stdout/stderr from your process (import errors, tracebacks).
- App won't start? Check that `app.yaml`'s `command` is right and every import is in `requirements.txt`.

Workspaces that support app-level Git sources can alternatively deploy a branch,
tag or commit directly. The Git-folder flow above is the setup verified for this
project and makes the pulled commit visible in the workspace before deployment.

## Hackathon advice

Deploy a hello-world **on day one**. Deployment friction is the classic hackathon killer, and "works reliably in a live demo on Free Edition" is 25% of the score. Keep `main` deployable and deploy from GitHub after each reviewed merge.

Next: [4 · Connecting data & persistence](04-data-and-persistence.md)
