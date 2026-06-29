from abc import ABC, abstractmethod

from app.models.pipeline import PipelineRun


class BaseAdapter(ABC):
    @abstractmethod
    def fetch_and_normalize(self, owner: str, repo: str, run_id: str) -> PipelineRun:
        ...
