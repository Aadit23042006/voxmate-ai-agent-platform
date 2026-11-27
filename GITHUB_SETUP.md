# GitHub Repository Setup

The ZIP contains the source tree, not account credentials or a pre-connected remote.
Create a new empty repository in your GitHub account, then run these commands
from this project directory:

```bash
git init
git branch -M main
git add .
git commit -m "Complete Task 5 AI agents and automation project"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

Before starting the app, copy `.env.example` to `.env` and set a unique,
strong `POSTGRES_PASSWORD` and `JWT_SECRET`. Add your Gemini and optional
integration credentials only to the local `.env`; never commit `.env`.

The company requires a GitHub repository URL. Creating/pushing it requires
the user's GitHub sign-in and repository choice, so the ZIP cannot claim that
this external submission has already been completed.


## Secret-scanning requirement

`mobile/google-services.json` is deliberately excluded from Git. A previous version contained a Google API key and was detected by GitHub. Rotate/restrict that key in Google Cloud/Firebase before continuing.

For this repository's existing one-commit history, use `CLEAN_GITHUB_SECRET.ps1` after the rotation, or manually create a clean history and force-push it. Do **not** treat deleting the file in a new commit as sufficient: the old commit still contains the credential.

After the force-push, verify GitHub **Settings → Code security and analysis → Secret scanning** / **Security** alerts. A previously detected credential should be marked resolved only after it has been revoked/rotated and the old reachable history is gone.
