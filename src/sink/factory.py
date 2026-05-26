#!/usr/bin/env python3

from multiprocessing import Queue
from os import getenv
from typing import List, Type

from .interface import Sink
from .json_file_sink import JsonFileSink
from .jsonl_file_sink import JsonlFileSink
from .print_sink import PrintSink
from src.types_ import ParsingResult

SinkClasses: List[Type[Sink]] = [JsonFileSink, JsonlFileSink, PrintSink]


class SinkFactory:

    @classmethod
    def get_sink(cls, in_queue: "Queue[ParsingResult]") -> Sink:
        sink_type = getenv("SINK_TYPE")

        assert (
            sink_type is not None
        ), "The env variable 'SINK_TYPE' has to be specified!"

        for SinkClass in SinkClasses:
            if SinkClass.TYPE == sink_type:
                return SinkClass(in_queue)

        raise NotImplementedError(
            f"The specified sink type '{sink_type}' does not have a corresponding implementation."
            f"Available types are: {cls.get_sink_types()}"
        )

    @classmethod
    def get_sink_types(cls) -> List[str]:
        return [SinkClass.TYPE for SinkClass in SinkClasses]
