from abc import ABC, abstractmethod
from typing import Any, Dict


class ToolError(Exception):
    pass


class BaseTool(ABC):
    name: str = "base_tool"

    @abstractmethod
    def validate(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate/normalize arguments. Raise ToolError if invalid."""
        raise NotImplementedError

    @abstractmethod
    def run(self, db, user, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool and return a JSON-serializable result."""
        raise NotImplementedError
