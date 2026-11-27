"""GitHub tools for the coding agent.

Read operations are automatic. Repository mutations are gated by the existing
VoxMate confirmation policy, so the user approves branch/file/PR changes.
"""
from app.tools.base import BaseTool, ToolError
from app.integrations.github import (
    get_token, list_repos, get_file, search_code, create_branch, write_file, create_pr,
    GitHubError,
)


def _token(db, user):
    token = get_token(db, user)
    if not token:
        raise ToolError("GitHub is not connected. Connect a GitHub account/token first.")
    return token


class GitHubListReposTool(BaseTool):
    name = "github_list_repos"
    def validate(self, arguments):
        return {"per_page": int((arguments or {}).get("per_page", 30))}
    def run(self, db, user, arguments):
        try:
            return {"repositories": [
                {"full_name": r["full_name"], "private": r["private"], "default_branch": r.get("default_branch"), "html_url": r["html_url"]}
                for r in list_repos(_token(db,user), arguments["per_page"])
            ]}
        except GitHubError as e:
            raise ToolError(str(e))


class GitHubGetFileTool(BaseTool):
    name = "github_get_file"
    def validate(self, arguments):
        a=arguments or {}
        for k in ("owner","repo","path"):
            if not a.get(k): raise ToolError(f"github_get_file requires '{k}'")
        return {"owner":a["owner"],"repo":a["repo"],"path":a["path"],"ref":a.get("ref")}
    def run(self, db, user, arguments):
        try: return get_file(_token(db,user), **arguments)
        except GitHubError as e: raise ToolError(str(e))


class GitHubSearchCodeTool(BaseTool):
    name = "github_search_code"
    def validate(self, arguments):
        q=(arguments or {}).get("query")
        if not q: raise ToolError("github_search_code requires 'query'")
        return {"query":q,"per_page":int((arguments or {}).get("per_page",20))}
    def run(self, db, user, arguments):
        try: return search_code(_token(db,user), **arguments)
        except GitHubError as e: raise ToolError(str(e))


class GitHubCreateBranchTool(BaseTool):
    name = "github_create_branch"
    def validate(self, arguments):
        a=arguments or {}
        for k in ("owner","repo","branch"):
            if not a.get(k): raise ToolError(f"github_create_branch requires '{k}'")
        return {"owner":a["owner"],"repo":a["repo"],"branch":a["branch"],"from_ref":a.get("from_ref","main")}
    def run(self, db, user, arguments):
        try:
            data=create_branch(_token(db,user), **arguments)
            return {"created":True,"ref":data.get("ref"),"sha":data.get("object",{}).get("sha")}
        except GitHubError as e: raise ToolError(str(e))


class GitHubWriteFileTool(BaseTool):
    name = "github_write_file"
    def validate(self, arguments):
        a=arguments or {}
        for k in ("owner","repo","path","content","message","branch"):
            if not a.get(k): raise ToolError(f"github_write_file requires '{k}'")
        if len(a["content"]) > 200_000: raise ToolError("File content exceeds the 200KB safety limit.")
        return {k:a.get(k) for k in ("owner","repo","path","content","message","branch","sha")}
    def run(self, db, user, arguments):
        try:
            data=write_file(_token(db,user), **arguments)
            return {"committed":True,"commit_sha":data.get("commit",{}).get("sha"),"content_url":data.get("content",{}).get("html_url")}
        except GitHubError as e: raise ToolError(str(e))


class GitHubCreatePRTool(BaseTool):
    name = "github_create_pr"
    def validate(self, arguments):
        a=arguments or {}
        for k in ("owner","repo","title","body","head"):
            if not a.get(k): raise ToolError(f"github_create_pr requires '{k}'")
        result = {k:a.get(k) for k in ("owner","repo","title","body","head")}
        result["base"] = a.get("base") or "main"
        return result
    def run(self, db, user, arguments):
        try:
            data=create_pr(_token(db,user), **arguments)
            return {"created":True,"number":data.get("number"),"url":data.get("html_url")}
        except GitHubError as e: raise ToolError(str(e))
