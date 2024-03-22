#!/usr/bin/env python3

from dotenv import load_dotenv
from multiprocessing import Queue, Process
from typing import List

from src.feeder import Feeder, FeederFactory
from src.processors import Processor, XmlParser
from src.sink import Sink, SinkFactory
from src.types_ import ParsingResult, XmlObject

load_dotenv()


def main():

    xml_object_queue: Queue[XmlObject] = Queue(1000)
    result_queue: Queue[ParsingResult] = Queue(1000)

    feeder: Feeder = FeederFactory.get_feeder(out_queue=xml_object_queue)

    parser: Processor = XmlParser(in_queue=xml_object_queue, out_queue=result_queue)
    sink: Sink = SinkFactory.get_sink(in_queue=result_queue)

    workers: List[Process] = []

    # Allocate workers based on which process step is the
    # bottleneck and how many resources are available.
    for _ in range(1):
        worker = Process(target=parser.run, daemon=True, args=())
        worker.start()
        workers.append(worker)

    for _ in range(1):
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
