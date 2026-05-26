#!/usr/bin/env python3

import json
from multiprocessing import Queue

from src.types_ import ParsingResult
from .interface import Sink


class PrintSink(Sink):
    """Print parsing results to stdout.
    Mostly used for debugging and testing.
    """

    TYPE: str = "print"

    in_queue: "Queue[ParsingResult]"

    def __init__(self, in_queue: "Queue[ParsingResult]") -> None:
        self.in_queue = in_queue

    def run(self) -> None:
        while True:
            parsing_result: ParsingResult = self.in_queue.get()

            if parsing_result is None:
                self.in_queue.put(None)  # Alert other workers
                break

            print(json.dumps(parsing_result.content, indent=4, ensure_ascii=False))
