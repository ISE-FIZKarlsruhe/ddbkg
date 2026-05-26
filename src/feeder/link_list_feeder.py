#!/usr/bin/env python3

from multiprocessing import Queue
from os import getenv
import requests
from typing import Any, List

from .interface import Feeder
from src.types_ import XmlObject


class LinkListFeeder(Feeder):
    """Fetch xml objects as text from a list of links."""

    TYPE: str = "link-list"

    out_queue: "Queue[XmlObject]"
    links: List[str]

    def __init__(self, out_queue: "Queue[XmlObject]") -> None:
        links_str = getenv("LINKS")

        assert links_str is not None, (
            f"If the feeder type '{self.TYPE}' is selected, the environment variable 'LINKS' "
            f"also has to be specified (comma separated)."
        )

        self.links = [link.strip() for link in links_str.split(",")]
        self.out_queue = out_queue

    def run(self) -> None:
        for link in self.links:
            response = requests.get(link)

            object_id = link.split("/")[-1]
            xml = response.text

            xml_object = XmlObject(text=xml, object_id=object_id)

            self.out_queue.put(xml_object)

        self.out_queue.put(None)
