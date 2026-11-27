from app.tools.base import BaseTool, ToolError
from app.agents.llm_client import web_search


class SearchTool(BaseTool):
    name = "search"

    def validate(self, arguments):
        query = (arguments or {}).get("query")
        if not query:
            raise ToolError("search requires a 'query'")
        return {"query": query}

    def run(self, db, user, arguments):
        args = self.validate(arguments)
        return web_search(args["query"])
