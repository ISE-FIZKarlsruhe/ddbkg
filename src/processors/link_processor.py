#!/usr/bin/env python3

from multiprocessing import Queue
import requests
from typing import List

from src.types_ import XmlObject
from .interface import Processor


class LinkProcessor(Processor):
    in_queue: "Queue[str]"
    out_queue: "Queue[XmlObject]"

    def __init__(self, in_queue: "Queue[str]", out_queue: "Queue[XmlObject]") -> None:
        self.in_queue = in_queue
        self.out_queue = out_queue

    def run(self) -> None:
        while True:
            link: str = self.in_queue.get()

            # TODO: Check if this is best way to detect
            # end of queue.
            if link is None:
                break

            response = requests.get(link)

            object_id = link.split("/")[-1]
            xml = response.text

            xml_object = XmlObject(text=xml, object_id=object_id)

            self.out_queue.put(xml_object)
