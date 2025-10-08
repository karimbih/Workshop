from abc import ABC, abstractmethod
from typing import Any, Dict

class Puzzle(ABC):
    @abstractmethod
    def get_prompt(self) -> Dict[str, Any]:
        ...
    @abstractmethod
    def validate(self, submission: Dict[str, Any]) -> bool:
        ...

