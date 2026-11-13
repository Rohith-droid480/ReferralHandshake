# Antigravity Agent Rules: Continuous GitHub Sync & Auto-Push

## 1. Target GitHub Repository Configuration

* **GitHub Repository URL:** https://github.com/Rohith-droid480/ReferralHandshake

* **Remote Name:** `origin`

* **Target Branch:** `main`

## 2. Repository Initialization & Remote Verification

Before executing any code changes or at the start of every session:

1. Check if the workspace is already a Git repository using `git status`.

2. If not initialized, initialize it on the `main` branch (`git init -b main`).

3. Check configured remotes using `git remote -v`.

   * If `origin` does not exist, add it: `git remote add origin <GitHub Repository URL>`

   * If `origin` points to a different URL, update it: `git remote set-url origin <GitHub Repository URL>`

## 3. Mandatory Regular Push Triggers

You MUST commit and push code regularly to the configured GitHub repository without waiting to be asked, specifically at every one of these checkpoints:

1. **Task Completion:** Immediately after completing any user prompt, feature, module, endpoint, UI screen, or bug fix.

2. **Test Pass:** Immediately after any test suite, linter, or verification script passes.

3. **Incremental Checkpoints:** After creating or modifying 3 or more files, or every 15 minutes during multi-step implementation tasks.

4. **Configuration & Docs Updates:** Whenever architecture docs, schemas, or configuration files are updated.

## 4. Pre-Push Safety & Hygiene Guardrails

Before staging or pushing any changes:

1. **Protect Secrets:** Never commit `.env` files, API keys, tokens, credentials, private keys, or local database dumps. Ensure `.gitignore` includes `.env`, `.env.*`, `*.pem`, `*.key`, `__pycache__/`, `node_modules/`, `.venv/`, and build output directories before running `git add`.

2. **Respect Locked Specifications:** Do not modify human-locked specification files, conformance test vectors, or `CODEOWNERS` files to force tests to pass.

3. **Verify Working State:** Ensure there are no broken syntax errors or half-written files before creating a commit.

## 5. Standard Commit & Push Execution Workflow

Whenever a push trigger is reached, execute these steps in order:

1. Run `git status` to inspect all untracked and modified files.

2. Stage changes cleanly (`git add .`).

3. Write a clear, concise Conventional Commit message (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, or `chore:`) summarizing what changed and why:
   `git commit -m "<type>(<scope>): <concise summary>"`

4. Sync with remote before pushing if remote history exists:
   `git pull --rebase origin main`

5. Push changes to GitHub:
   `git push -u origin main`

## 6. Failure Handling

* If `git push` fails due to authentication prompts, branch protection, network disconnection, or rebase conflicts, **stop and report the exact terminal error** to the user immediately so it can be resolved. Never silently ignore a failed push.