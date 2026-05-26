#!/usr/bin/env python3

import argparse
import json
import logging
from multiprocessing import Queue
import os
import re
from typing import Any, Dict, List
from xml.etree import ElementTree as ET
import xmltodict

from .interface import Processor
from src.types_ import XmlObject, ParsingResult


CLASSES = [
    "ProvidedCHO",
    "PhysicalThing",
    "Agent",
    "Event",
    "Place",
    "TimeSpan",
    "Concept",
    "Aggregation",
    "WebResource",
    "ProvenanceStatement",
    "LinguisticSystem",
]

PREFIXES = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
    "http://www.openarchives.org/ore/terms/": "ore",
    "http://www.europeana.eu/schemas/edm/": "edm",
    "http://purl.org/dc/elements/1.1/": "dc",
    "http://purl.org/dc/terms/": "dcterms",
    "http://www.w3.org/2004/02/skos/core#": "skos",
    "http://www.w3.org/2003/01/geo/wgs84_pos#": "wgs84_pos",
    "http://www.cidoc-crm.org/rdfs/cidoc_crm_v5.0.2_english_label.rdfs#": "crm",
    "http://www.deutsche-digitale-bibliothek.de/edm/": "ddb",
}

# XML Parser


def arg_parser() -> Dict[str, Any]:
    """
    Parse command line arguments.
    :return: Parsed arguments as a dictionary.
    """
    args = argparse.ArgumentParser()
    # parser.add_argument("--num", type=int, default=-1, help="number of files to extract text, without setting it, default all.")
    args.add_argument(
        "--config",
        type=str,
        default=os.path.join(os.getcwd(), "config-audio.json"),
        help="Path to config file.",
    )
    args.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Prints debug messages.",
    )

    return vars(args.parse_args())


class XmlDictConfig(dict):
    """Adapted From https://stackoverflow.com/a/5807028"""

    def convert_tag(self, tag):
        (prefix, PROP) = tag.split("}")
        prefix = PREFIXES.get(prefix[1:], "")
        PROP = f"{prefix}:{PROP}"

        return PROP

    def __init__(self, parent_element, parent_tag=""):
        # parent_element attributes
        if parent_element.items():
            logging.debug(f"ATTRIB: {parent_element.items()}")
            self.update(dict(parent_element.items()))

        for element in parent_element:
            if element:
                # treat like dict - we assume that if the first two tags
                # in a series are different, then they are all different.
                # [Ann] changed to fix TVDCIJ7DGHUXUQ35YYQHHRRGESBB5XY6
                tags = []
                for member in element:
                    tags.append(member.tag)

                if len(element) == 1 or len(set(tags)) > 1:
                    aDict = XmlDictConfig(element, self.convert_tag(element.tag))
                # treat like list - we assume that if the first two tags
                # in a series are the same, then the rest are the same.
                else:
                    # here, we put the list in dictionary; the key is the
                    # tag name the list elements all share in common, and
                    # the value is the list itself
                    aDict = {self.convert_tag(element[0].tag): XmlListConfig(element)}

                # if the tag has attributes, add those to the dict
                if element.items():
                    aDict.update(dict(element.items()))
                    if "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about" in aDict:
                        aDict["id"] = aDict.pop(
                            "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"
                        )
                        if aDict["id"].startswith(
                            "http://www.deutsche-digitale-bibliothek.de/"
                        ):
                            aDict["id"] = aDict["id"].split("/")[-1]

                tag = self.convert_tag(element.tag)

                if not tag in self:
                    self.update({self.convert_tag(element.tag): aDict})
                else:
                    if isinstance(self[tag], list):
                        self[tag].append(aDict)
                    else:
                        self[tag] = [self[tag], aDict]

            # this assumes that if you've got an attribute in a tag,
            # you won't be having any text. This may or may not be a
            # good idea -- time will tell. It works for the way we are
            # currently doing XML configuration files...
            elif element.items():
                tag = self.convert_tag(element.tag)
                value = None
                items = (
                    element.items()
                )  # list of tuples Example: [('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', 'http://terminology.lido-schema.org/eventType/publication')]

                if (
                    items[0][0]
                    == "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"
                ):
                    value = items[0][1]
                elif items[0][0] == "{http://www.w3.org/XML/1998/namespace}lang":
                    value = {"lang": items[0][1]}
                else:
                    value = dict(items)

                # print(f'TAG [{tag}] [{value}]')
                if element.text:
                    if isinstance(value, dict):
                        value.update({"text": element.text})
                    elif isinstance(value, str):
                        value = {"id": value, "text": element.text}

                if not tag in self:
                    self.update({tag: value})
                else:
                    if isinstance(self[tag], list):
                        self[tag].append(value)
                    else:
                        self[tag] = [self[tag], value]

            # finally, if there are no child tags and no attributes, extract
            # the text
            else:
                tag = self.convert_tag(element.tag)
                value = element.text

                if not tag in self:
                    self.update({tag: value})
                else:
                    if isinstance(self[tag], list):
                        self[tag].append(value)
                    else:
                        self[tag] = [self[tag], value]


class XmlListConfig(list):
    """From https://stackoverflow.com/a/5807028"""

    def convert_tag(self, tag):
        (prefix, PROP) = tag.split("}")
        prefix = PREFIXES.get(prefix[1:], "")
        PROP = f"{prefix}:{PROP}"

        return PROP

    def __init__(self, aList):
        for element in aList:
            if element:
                # treat like dict
                if len(element) == 1 or element[0].tag != element[1].tag:
                    self.append(XmlDictConfig(element))
                # treat like list
                elif element[0].tag == element[1].tag:
                    self.append(XmlListConfig(element))
            elif element.text:
                text = element.text.strip()

                if text:
                    self.append(text)


class OriginalParser:
    object_dict: Dict = dict()
    view_fields: Dict = dict()
    provenance_fields: Dict = dict()

    valid_elems = [
        "cortex",
        "edm",
        "RDF",
        "view",
        "item",
        "fields",
        "properties",
        "provider-info",
        "source",
    ]

    handlers = {
        "RDF": "parse_edm",
        "fields": "parse_view",
        "properties": "parse_provenance",
        "provider-info": "parse_provider",
        "source": "parse_source",
    }

    object_id: str = None

    def __init__(self):
        pass

    def set_objid(self, object_id: str):
        self.object_id = object_id

    def parse_edm(self, root):
        tag = root.tag.split("}")[-1]

        self.object_dict = XmlDictConfig(root)

    def parse_view(self, root):
        if root.attrib["usage"] == "display":
            for elem in root:
                key = ""
                for field in elem:
                    logging.debug(f"FIELD: [{field.tag}] [{field}]")
                    if field.tag.endswith("name"):
                        key = field.text
                    elif field.tag.endswith("value"):
                        self.view_fields[key] = field.text
        else:
            return

    def parse_source(self, root):
        for elem in root:
            if elem.tag.endswith("record"):
                self.provenance_fields["source-type"] = elem.attrib["type"]
                if elem.attrib["type"] == "http://www.lido-schema.org/":
                    """
                    <lido:conceptID lido:source="iconclass" lido:type="uri">http://iconclass.org/rkd/71/</lido:conceptID>
                    """

                    for ic_code in re.findall(
                        r"source\=\"iconclass\"[^\>]+\>(http[^\<]+)\<\/", elem.text
                    ):
                        if not "source-ic" in self.provenance_fields:
                            self.provenance_fields["source-ic"] = []
                        self.provenance_fields["source-ic"].append(ic_code)

                    lido_obj = xmltodict.parse(elem.text)
                    # print(json.dumps(lido_obj, indent=4, ensure_ascii=False))
                    self.provenance_fields["lido-source"] = lido_obj

            elif elem.tag.endswith("description"):
                for field in elem:
                    if field.tag.endswith("record"):
                        ref = field.attrib["ref"]
                        if self.object_id != ref:
                            self.provenance_fields["source-ref"] = field.attrib["ref"]

                        self.provenance_fields["source-type"] = field.attrib["type"]

    def parse_provenance(self, root):
        for elem in root:
            self.provenance_fields[elem.tag.split("}")[-1]] = elem.text

    def parse_provider(self, root):
        details_to_save = [
            "provider-name",
            "provider-uri",
            "provider-id",
            "provider-ddb-id",
            "provider-isil",
        ]
        self.provenance_fields["provider"] = dict()
        for elem in root:
            field = elem.tag.split("}")[-1]
            if field in details_to_save:
                self.provenance_fields["provider"][
                    "".join(field.split("-")[1:])
                ] = elem.text

    def parse_recursively(self, root):
        """Design pattern from https://stackoverflow.com/a/28195289"""

        tag = root.tag.split("}")[-1]

        if not tag in self.valid_elems:
            logging.debug(f"IGNORED: TAG [{tag}]")
            return

        if tag in self.handlers:
            # See https://stackoverflow.com/a/12921884
            getattr(self, self.handlers[tag])(root)

        else:
            for elem in root:
                self.parse_recursively(elem)

    def parse_xml(self, resp_text: str):
        root = ET.fromstring(resp_text)
        self.parse_recursively(root)

        self.object_dict["View"] = self.view_fields.copy()
        self.object_dict["Prov"] = self.provenance_fields.copy()
        self.view_fields.clear()
        self.provenance_fields.clear()

        return self.object_dict


class XmlParser(Processor):
    """Parse xml objects from text according to the parsing 
    logic of Ann Tan.
    """

    in_queue: "Queue[XmlObject]"
    out_queue: "Queue[ParsingResult]"
    _parser: OriginalParser

    def __init__(
        self, in_queue: "Queue[XmlObject]", out_queue: "Queue[ParsingResult]"
    ) -> None:
        self.in_queue = in_queue
        self.out_queue = out_queue

        # Separate original parsing logic
        # from multiprocessing wrapper class.
        self._parser = OriginalParser()

    def run(self) -> None:
        while True:
            xml_object: XmlObject = self.in_queue.get()

            if xml_object is None:
                self.in_queue.put(None)  # Alert other workers
                break

            self._parser.set_objid(xml_object.object_id)
            result_content: Dict = self._parser.parse_xml(xml_object.text)

            parsing_result = ParsingResult(
                content=result_content, object_id=xml_object.object_id
            )
            self.out_queue.put(parsing_result)

        self.out_queue.put(None)
