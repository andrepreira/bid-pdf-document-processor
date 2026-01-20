"""Centralized PDF reader mocks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class FakePage:
    text: str

    def extract_text(self) -> str:
        return self.text


class FakePdfReader:
    def __init__(self, pages: List[FakePage]):
        self.pages = pages
