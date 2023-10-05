from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Domain:
    code: str
    origin: str

@dataclass
class Sourcelink:
    sourceId: int
    value: str
    name: Optional[str] = ''

@dataclass
class Definition:
    value: str
    lang: str
    definitionTypeCode: str
    sourceLinks: List[Sourcelink] = field(default_factory=list)

@dataclass
class Note:
    value: str
    lang: str
    publicity: bool
    sourceLinks: List[Sourcelink] = field(default_factory=list)

@dataclass
class Lexemenote:
    value: str
    lang: str
    publicity: bool
    sourceLinks: List[Sourcelink] = field(default_factory=list)

@dataclass
class Forum:
    value: str

@dataclass
class Usage:
    value: str
    lang: str
    publicity: bool
    sourceLinks: List[Sourcelink] = field(default_factory=list)

@dataclass
class Word:
    value: str
    lang: str
    lexemeValueStateCode: Optional[str] = None
    lexemePublicity: Optional[bool] = True
    wordTypeCodes: List[str] = field(default_factory=list)
    usages: List[Usage] = field(default_factory=list)
    lexemeNotes: List[Lexemenote] = field(default_factory=list)
    lexemeSourceLinks: List[Sourcelink] = field(default_factory=list)


@dataclass
class Concept:
    datasetCode: str
    manualEventOn: str
    manualEventBy: str
    firstCreateEventOn: str
    firstCreateEventBy: str
    domains: List[Domain] = field(default_factory=list)
    definitions: List[Definition] = field(default_factory=list)
    notes: List[Note] = field(default_factory=list)
    forums: List[Forum] = field(default_factory=list)
    words: List[Word] = field(default_factory=list)
    conceptIds: List[str] = field(default_factory=list)
