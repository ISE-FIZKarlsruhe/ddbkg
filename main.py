#!/usr/bin/env python3

from dotenv import load_dotenv
from multiprocessing import Queue, Process
from os import getenv
from typing import List

from src.feeder import Feeder, FeederFactory
from src.processors import Processor, XmlParser
from src.sink import Sink, SinkFactory
from src.types_ import ParsingResult, XmlObject

load_dotenv()


def main():

    parser_worker_count = getenv("PARSER_WORKER_COUNT")
    if parser_worker_count is None:
        parser_worker_count = 1
    else:
        parser_worker_count = int(parser_worker_count.strip())
    
    sink_worker_count = getenv("SINK_WORKER_COUNT")
    if sink_worker_count is None:
        sink_worker_count = 1
    else:
        sink_worker_count = int(sink_worker_count.strip())

    xml_object_queue: Queue[XmlObject] = Queue(1000)
    result_queue: Queue[ParsingResult] = Queue(1000)

    feeder: Feeder = FeederFactory.get_feeder(out_queue=xml_object_queue)

    parser: Processor = XmlParser(in_queue=xml_object_queue, out_queue=result_queue)
    sink: Sink = SinkFactory.get_sink(in_queue=result_queue)

    workers: List[Process] = []
    for _ in range(parser_worker_count):
        worker = Process(target=parser.run, daemon=True, args=())
        worker.start()
        workers.append(worker)

    for _ in range(sink_worker_count):
        worker = Process(target=sink.run, daemon=True, args=())
        worker.start()
        workers.append(worker)

    # To avoid race conditions if one feeder process finishes before the
    # other, run feeder only in a single process.
    feeder.run()

    for worker in workers:
        worker.join()


if __name__ == "__main__":
    main()
