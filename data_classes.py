from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Domain:
    value: str

@dataclass
class Definition:
    value: str
    lang: str
    definitionTypeCode: str
    source: str

@dataclass
class Note:
    value: str
    lang: str
    is_public: int

@dataclass
class Forum:
    value: str

@dataclass
class Usage:
    value: str
    is_public: int

@dataclass
class Word:
    value: str
    lang: str
    is_public: int
    word_type: Optional[str] = None
    value_state_code: Optional[str] = None
    usage: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

@dataclass
class Concept:
    domains: list = field(default_factory=list)
    definitions: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    forum: list = field(default_factory=list)
    words: list = field(default_factory=list)