from app.utils.datetime import utcnow
"""Small GitHub REST client used by VoxMate's coding agent.

The integration is intentionally additive: existing tools keep their current
behavior. GitHub credentials are per-user and are never exposed to Gemini.
"""
import base64
import json
from typing import Any, Optional
import httpx
from cryptography.fernet import Fernet
from app.config import settings

API = "https://api.github.com"


class GitHubError(RuntimeError):
    pass


def _fernet() -> Fernet:
    key = settings.github_token_encryption_key.strip()
    if not key:
        raise GitHubError(
            "GitHub integration is not configured. Set GITHUB_TOKEN_ENCRYPTION_KEY in .env."
        )
    try:
        return Fernet(key.encode())
    except Exception as exc:
        raise GitHubError("GITHUB_TOKEN_ENCRYPTION_KEY is not a valid Fernet key.") from exc


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


def save_token(db, user, token: str):
    from app.models.models import GitHubConnection
    row = db.query(GitHubConnection).filter(GitHubConnection.user_id == user.id).first()
    info = _request("GET", "/user", token)
    if row is None:
        row = GitHubConnection(user_id=user.id)
        db.add(row)
    row.encrypted_token = encrypt_token(token)
    row.login = info.get("login")
    row.scope = info.get("plan", {}).get("name") if isinstance(info.get("plan"), dict) else None
    from datetime import datetime
    row.updated_at = utcnow()
    db.commit()
    return {"connected": True, "login": row.login}


def get_token(db, user) -> Optional[str]:
    from app.models.models import GitHubConnection
    row = db.query(GitHubConnection).filter(GitHubConnection.user_id == user.id).first()
    if not row:
        return None
    return decrypt_token(row.encrypted_token)


def disconnect(db, user):
    from app.models.models import GitHubConnection
    row = db.query(GitHubConnection).filter(GitHubConnection.user_id == user.id).first()
    if row:
        db.delete(row)
        db.commit()
    return {"connected": False}


def status(db, user):
    from app.models.models import GitHubConnection
    row = db.query(GitHubConnection).filter(GitHubConnection.user_id == user.id).first()
    return {"connected": bool(row), "login": row.login if row else None}


def _request(method: str, path: str, token: str, **kwargs):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "VoxMate-Coding-Agent",
    }
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.request(method, API + path, headers=headers, **kwargs)
    if response.status_code >= 400:
        try:
            detail = response.json().get("message", response.text)
        except Exception:
            detail = response.text
        raise GitHubError(f"GitHub API {response.status_code}: {detail}")
    return response.json() if response.content else {}


def list_repos(token: str, per_page: int = 30):
    return _request("GET", f"/user/repos?sort=updated&per_page={min(max(per_page,1),100)}", token)


def get_file(token: str, owner: str, repo: str, path: str, ref: Optional[str] = None):
    params = {"ref": ref} if ref else {}
    data = _request("GET", f"/repos/{owner}/{repo}/contents/{path.lstrip('/')}", token, params=params)
    if isinstance(data, list):
        raise GitHubError("The requested path is a directory, not a file.")
    raw = base64.b64decode(data["content"].replace("\n", "")).decode("utf-8", errors="replace")
    return {"path": data["path"], "sha": data["sha"], "size": data.get("size"), "content": raw, "html_url": data.get("html_url")}


def search_code(token: str, query: str, per_page: int = 20):
    data = _request("GET", "/search/code", token, params={"q": query, "per_page": min(max(per_page,1),50)})
    return {"total_count": data.get("total_count", 0), "items": [
        {"name": x.get("name"), "path": x.get("path"), "repository": x.get("repository", {}).get("full_name"), "html_url": x.get("html_url")}
        for x in data.get("items", [])
    ]}


def create_branch(token: str, owner: str, repo: str, branch: str, from_ref: str = "main"):
    ref = _request("GET", f"/repos/{owner}/{repo}/git/ref/heads/{from_ref}", token)
    sha = ref["object"]["sha"]
    return _request("POST", f"/repos/{owner}/{repo}/git/refs", token, json={"ref": f"refs/heads/{branch}", "sha": sha})


def write_file(token: str, owner: str, repo: str, path: str, content: str, message: str, branch: str, sha: Optional[str] = None):
    body = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if sha:
        body["sha"] = sha
    return _request("PUT", f"/repos/{owner}/{repo}/contents/{path.lstrip('/')}", token, json=body)


def create_pr(token: str, owner: str, repo: str, title: str, body: str, head: str, base: str = "main"):
    return _request("POST", f"/repos/{owner}/{repo}/pulls", token, json={
        "title": title, "body": body, "head": head, "base": base,
    })

