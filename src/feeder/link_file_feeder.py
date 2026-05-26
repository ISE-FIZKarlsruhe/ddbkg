#!/usr/bin/env python3

from multiprocessing import Queue
from os import getenv
import requests
from typing import Any, List

from .interface import Feeder
from src.types_ import XmlObject


class LinkFileFeeder(Feeder):
    """Fetch xml objects as text from a file that contains links
    separated by new line.."""

    TYPE: str = "link-file"

    out_queue: "Queue[XmlObject]"
    links: List[str]

    def __init__(self, out_queue: "Queue[XmlObject]") -> None:
        path = getenv("LINK_FILE_PATH")

        assert path is not None, (
            f"If the feeder type '{self.TYPE}' is selected, the environment variable "
            "'LINK_FILE_PATH' also has to be specified."
        )

        self.links = self.load_links(path)
        self.out_queue = out_queue

    def load_links(self, path: str) -> List[str]:
        with open(path) as link_file:
            links = [line.strip() for line in link_file]
            return links

    def run(self) -> None:
        for link in self.links:
            response = requests.get(link)

            object_id = link.split("/")[-1]
            xml = response.text

            xml_object = XmlObject(text=xml, object_id=object_id)

            self.out_queue.put(xml_object)

        self.out_queue.put(None)
