#!/usr/bin/env python3

from multiprocessing import Queue
from os import getenv
import sqlite3
from typing import Any, List

from .interface import Feeder
from src.types_ import XmlObject


class Sqlite3Feeder(Feeder):
    """Load xml objects as text from an sqlite3 database."""

    TYPE: str = "sqlite3"

    out_queue: "Queue[XmlObject]"
    db_path: str

    def __init__(self, out_queue: "Queue[XmlObject]") -> None:
        db_path = getenv("SQLITE3_PATH")

        assert db_path is not None, (
            f"If the feeder type '{self.TYPE}' is selected, the environment variable "
            "'SQLITE3_PATH' also has to be specified."
        )

        self.db_path = db_path
        self.out_queue = out_queue

    def run(self) -> None:
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM source")

        for objid, last_download, xml in cursor:
            xml_object = XmlObject(text=xml, object_id=objid)
            self.out_queue.put(xml_object)

        cursor.close()
        connection.close()

        self.out_queue.put(None)
