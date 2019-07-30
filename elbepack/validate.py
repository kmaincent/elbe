# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2017 Benedikt Spranger <b.spranger@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys

from lxml import etree
from lxml.etree import XMLParser, parse

from elbepack.shellhelper import CommandError
from elbepack.xmlpreprocess import PreprocessWrapper, error_log_to_strings


def validate_xml(fname):
    if os.path.getsize(fname) > (1 << 30):
        return ["%s is greater than 1 GiB. "
                "Elbe does not support files of this size." % fname]

    schema_file = "https://www.linutronix.de/projects/Elbe/dbsfed.xsd"
    parser = XMLParser(huge_tree=True)
    schema_tree = etree.parse(schema_file)
    schema = etree.XMLSchema(schema_tree)

    try:
        with PreprocessWrapper(fname) as xml_p:
            xml = parse(xml_p.preproc, parser=parser)
            try:
                if schema.validate(xml):
                    return validate_xml_content(xml)
            except etree.XMLSyntaxError:
                return ["XML Parse error\n" + str(sys.exc_info()[1])]
            except BaseException:
                return ["Unknown Exception during validation\n" +
                        str(sys.exc_info()[1])]
    except CommandError as E:
        return ["Fail preprocessor\n%r" % E]

    # We have errors, return them in string form...
    return error_log_to_strings(schema.error_log)


def validate_xml_content(xml):
    errors = []

    dbsv = xml.find("/target/debootstrapvariant")

    if (dbsv is not None and "minbase" in dbsv.text
            and "gnupg" not in dbsv.get("includepkgs", "")
            and xml.find("/project/mirror/url-list/url/key") is not None):

        errors.append("\nThe XML contains a custom mirror key. "
                      "Use debootstrapvariant's attribute includepkgs "
                      "to make gnupg available in debootstrap.\n")

    primary_proto = xml.findtext("/project/mirror/primary_proto", "")
    https = (primary_proto.lower() == "https")

    if (not https
        and (dbsv is None
             or "apt-transport-https" not in dbsv.get("includepkgs", ""))):
        for url in xml.findall("/project/mirror/url-list/url"):
            b = url.findtext("binary", "")
            s = url.findtext("source", "")
            if b.startswith("https") or s.startswith("https"):
                errors.append("\nThe XML contains an HTTPS mirror. "
                              "Use debootstrapvariant's attribute includepkgs "
                              "to make apt-transport-https available in "
                              "debootstrap.\n")
                break

    return errors
