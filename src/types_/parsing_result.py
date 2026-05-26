#!/usr/bin/env python3

from dataclasses import dataclass
from typing import Dict


@dataclass
class ParsingResult:
    content: Dict
    object_id: str
