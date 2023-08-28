from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Domain:
    code: str
    origin: str

@dataclass
class sourceLink:
    sourceId: int
    searchValue: str
    value: str

@dataclass
class Definition:
    value: str
    lang: str
    definitionTypeCode: str
    sourceLinks: List[sourceLink] = field(default_factory=list)

@dataclass
class Note:
    value: str
    lang: str
    publicity: bool
    sourceLinks: List[sourceLink] = field(default_factory=list)

@dataclass
class lexemeNote:
    value: str
    lang: str
    publicity: bool
    sourceLinks: List[sourceLink] = field(default_factory=list)

@dataclass
class Forum:
    value: str

@dataclass
class Usage:
    value: str
    lang: str
    publicity: bool
    sourceLinks: List[sourceLink] = field(default_factory=list)

@dataclass
class Word:
    value: str
    lang: str
    lexemeValueStateCode: Optional[str] = None
    lexemePublicity: Optional[bool] = True
    wordTypeCodes: List[str] = field(default_factory=list)
    usages: List[Usage] = field(default_factory=list)
    lexemeNotes: List[lexemeNote] = field(default_factory=list)
    lexemeSourceLinks: List[sourceLink] = field(default_factory=list)

@dataclass
class Concept:
    datasetCode: str
    domains: List[Domain] = field(default_factory=list)
    definitions: List[Definition] = field(default_factory=list)
    notes: List[Note] = field(default_factory=list)
    forums: List[Forum] = field(default_factory=list)
    words: List[Word] = field(default_factory=list)