#!/usr/bin/env python3

import json
from multiprocessing import Queue
import os
from os import getenv
from typing import List
from uuid import uuid4

from src.types_ import ParsingResult
from .interface import Sink


class JsonlFileSink(Sink):
    """Store parsing results in bulks to jsonl files."""

    TYPE: str = "jsonl"

    in_queue: "Queue[ParsingResult]"
    target_dir: str
    batch_size: int

    def __init__(self, in_queue: "Queue[ParsingResult]") -> None:
        target_dir = getenv("SINK_TARGET_DIR")

        if target_dir is None:
            target_dir = "tmp"

        batch_size = getenv("BATCH_SIZE")

        if batch_size is None:
            batch_size = 10
        else:
            batch_size = int(batch_size.strip())

        self.target_dir = target_dir
        self.in_queue = in_queue
        self.batch_size = batch_size

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

    def run(self) -> None:
        batch_results: List[ParsingResult] = []
        while True:
            parsing_result: ParsingResult = self.in_queue.get()

            if parsing_result is None:
                self.in_queue.put(None)  # Alert other workers
                self.store_batch(batch_results)
                break

            batch_results.append(parsing_result)

            if len(batch_results) >= self.batch_size:
                self.store_batch(batch_results)
                batch_results = []

    def store_batch(self, parsing_results: List[ParsingResult]) -> None:
        target_path = f"{self.target_dir}/{uuid4()}.jsonl"
        with open(target_path, "w") as target_file:
            for result in parsing_results:
                target_file.write(json.dumps([result.object_id, result.content]) + "\n")
