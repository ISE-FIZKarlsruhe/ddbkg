#!/usr/bin/env python3

from abc import abstractmethod, abstractproperty, ABC
from multiprocessing import Queue
from typing import Any

from src.types_ import XmlObject, ParsingResult


class Processor(ABC):
    """Get xml objects from a queue, parse them accordingly
    and put the result in an output queue for downstream
    tasks to process/store.
    """

    in_queue: "Queue[XmlObject]"
    out_queue: "Queue[ParsingResult]"

    @abstractmethod
    def __init__(
        self, in_queue: "Queue[XmlObject]", out_queue: "Queue[ParsingResult]"
    ) -> None: ...

    @abstractmethod
    def run(self) -> None: ...
