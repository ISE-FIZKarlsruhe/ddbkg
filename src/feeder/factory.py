#!/usr/bin/env python3

from multiprocessing import Queue
from os import getenv
from typing import List, Type

from .interface import Feeder
from .link_file_feeder import LinkFileFeeder
from .link_list_feeder import LinkListFeeder
from .sqlite3_feeder import Sqlite3Feeder
from src.types_ import XmlObject

FeederClasses: List[Type[Feeder]] = [LinkFileFeeder, LinkListFeeder, Sqlite3Feeder]


class FeederFactory:

    @classmethod
    def get_feeder(cls, out_queue: "Queue[XmlObject]") -> Feeder:
        feeder_type = getenv("FEEDER_TYPE")

        assert (
            feeder_type is not None
        ), "The env variable 'FEEDER_TYPE' has to be specified!"

        for FeederClass in FeederClasses:
            if FeederClass.TYPE == feeder_type:
                return FeederClass(out_queue)

        raise NotImplementedError(
            f"The specified feeder type '{feeder_type}' does not have a corresponding implementation."
            f"Available types are: {cls.get_feeder_types()}"
        )

    @classmethod
    def get_feeder_types(cls) -> List[str]:
        return [FeederClass.TYPE for FeederClass in FeederClasses]
