#!/usr/bin/env python3

from abc import abstractmethod, abstractproperty, ABC
from multiprocessing import Queue
from typing import Any

from src.types_ import XmlObject


class Feeder(ABC):
    """Load xml objects as text from a source and put
    them in a queue for downstream tasks to process.
    """

    TYPE: str

    out_queue: "Queue[XmlObject]"

    @abstractmethod
    def __init__(self, out_queue: "Queue[XmlObject]") -> None: ...

    @abstractmethod
    def run(self) -> None: ...
