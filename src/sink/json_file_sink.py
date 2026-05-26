#!/usr/bin/env python3

import json
from multiprocessing import Queue
import os
from os import getenv

from src.types_ import ParsingResult
from .interface import Sink


class JsonFileSink(Sink):
    """Store parsing results as json files to a specified
    directory."""

    TYPE: str = "json"

    in_queue: "Queue[ParsingResult]"
    target_dir: str

    def __init__(self, in_queue: "Queue[ParsingResult]") -> None:
        target_dir = getenv("SINK_TARGET_DIR")

        if target_dir is None:
            target_dir = "tmp"

        self.target_dir = target_dir
        self.in_queue = in_queue

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

    def run(self) -> None:
        while True:
            parsing_result: ParsingResult = self.in_queue.get()

            if parsing_result is None:
                self.in_queue.put(None)  # Alert other workers
                break

            file_path = f"{self.target_dir}/{parsing_result.object_id}.json"
            with open(file_path, "w") as target_file:
                json.dump(parsing_result.content, target_file, indent=4)
