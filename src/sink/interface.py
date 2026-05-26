#!/usr/bin/env python3

from abc import abstractmethod, abstractproperty, ABC
from multiprocessing import Queue

from src.types_ import ParsingResult


class Sink(ABC):
    """Get parsing results from a queue and store them
    accordingly.
    """

    TYPE: str

    in_queue: "Queue[ParsingResult]"

    @abstractmethod
    def __init__(self, in_queue: "Queue[ParsingResult]") -> None: ...

    @abstractmethod
    def run(self) -> None: ...
