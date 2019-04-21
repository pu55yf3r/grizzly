# coding=utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os
import shutil
import tempfile
import unittest

from grizzly.corpman import adapters

# configure logger here
log_level = logging.INFO
log_fmt = "[%(asctime)s] %(message)s"
if bool(os.getenv("DEBUG")):
    log_level = logging.DEBUG
    log_fmt = "%(levelname).1s %(name)s [%(asctime)s] %(message)s"
    logging.basicConfig(format=log_fmt, datefmt="%Y-%m-%d %H:%M:%S", level=log_level)


class AdapterLoaderTests(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_adapt_")
        adapters.__adapters__ = dict()

    def tearDown(self):
        if os.path.isdir(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_01(self):
        "test calling load() on a directory without adapters"
        os.makedirs(os.path.join(self.test_dir, "empty"))
        with open(os.path.join(self.test_dir, "empty_file"), "w") as _:
            pass
        with open(os.path.join(self.test_dir, "fake.py"), "w") as _:
            pass
        adapters.load(path=self.test_dir)
        self.assertFalse(adapters.__adapters__)

    def test_02(self):
        "test load() with an Adapter"
        os.makedirs(os.path.join(self.test_dir, "SimpleAdapter"))
        with open(os.path.join(self.test_dir, "SimpleAdapter", "__init__.py"), "w") as ofp:
            ofp.write("import grizzly.corpman\n")
            ofp.write("class SimpleAdapter(grizzly.corpman.Adapter):\n")
            ofp.write("\tNAME = 'simple'\n")
            ofp.write("\tdef setup(*_): pass\n")
            ofp.write("\tdef generate(*_): pass\n\n")
        adapters.load(path=self.test_dir, skip_failures=False)
        self.assertTrue(adapters.__adapters__)
        self.assertIn("simple", adapters.names())
        self.assertIsNotNone(adapters.get("simple"))
        # load() should only allowed once
        with self.assertRaises(AssertionError):
            adapters.load(path=self.test_dir)

    def test_03(self):
        "test load() with invalid NAME"
        # upper case in NAME
        os.makedirs(os.path.join(self.test_dir, "UpperAdapter"))
        with open(os.path.join(self.test_dir, "UpperAdapter", "__init__.py"), "w") as ofp:
            ofp.write("import grizzly.corpman\n")
            ofp.write("class UpperAdapter(grizzly.corpman.Adapter):\n")
            ofp.write("\tNAME = 'UppER'\n")
        with self.assertRaises(RuntimeError):
            adapters.load(path=self.test_dir)
        self.assertFalse(adapters.__adapters__)

    def test_04(self):
        "test load() with missing NAME"
        os.makedirs(os.path.join(self.test_dir, "AAdapter"))
        with open(os.path.join(self.test_dir, "AAdapter", "__init__.py"), "w") as ofp:
            ofp.write("import grizzly.corpman\n")
            ofp.write("class AAdapter(grizzly.corpman.Adapter):\n")
            ofp.write("\tpass\n")
        with self.assertRaises(RuntimeError):
            adapters.load(path=self.test_dir)
        self.assertFalse(adapters.__adapters__)

    def test_05(self):
        "test load() with name collision"
        os.makedirs(os.path.join(self.test_dir, "N1Adapter"))
        with open(os.path.join(self.test_dir, "N1Adapter", "__init__.py"), "w") as ofp:
            ofp.write("import grizzly.corpman\n")
            ofp.write("class N1Adapter(grizzly.corpman.Adapter):\n")
            ofp.write("\tNAME = 'adpt'\n")
        os.makedirs(os.path.join(self.test_dir, "N2Adapter"))
        with open(os.path.join(self.test_dir, "N2Adapter", "__init__.py"), "w") as ofp:
            ofp.write("import grizzly.corpman\n")
            ofp.write("class N2Adapter(grizzly.corpman.Adapter):\n")
            ofp.write("\tNAME = 'adpt'\n")
        with self.assertRaises(RuntimeError):
            adapters.load(path=self.test_dir)

    def test_06(self):
        "test load() with an Adapter (ignore other failures)"
        os.makedirs(os.path.join(self.test_dir, "EmptyAdapter"))
        with open(os.path.join(self.test_dir, "EmptyAdapter", "__init__.py"), "w") as ofp:
            ofp.write("\n")
        os.makedirs(os.path.join(self.test_dir, "BadAdapter"))
        with open(os.path.join(self.test_dir, "BadAdapter", "__init__.py"), "w") as ofp:
            ofp.write("import missinglib\n")
        os.makedirs(os.path.join(self.test_dir, "GoodAdapter"))
        with open(os.path.join(self.test_dir, "GoodAdapter", "__init__.py"), "w") as ofp:
            ofp.write("import grizzly.corpman\n")
            ofp.write("class GoodAdapter(grizzly.corpman.Adapter):\n")
            ofp.write("\tNAME = 'good'\n")
            ofp.write("\tdef setup(*_): pass\n")
            ofp.write("\tdef generate(*_): pass\n\n")
        adapters.load(path=self.test_dir)
        self.assertTrue(adapters.__adapters__)
        self.assertIn("good", adapters.names())
        self.assertIsNotNone(adapters.get("good"))

    def test_07(self):
        "test load() with broken Adapter"
        os.makedirs(os.path.join(self.test_dir, "BadAdapter"))
        with open(os.path.join(self.test_dir, "BadAdapter", "__init__.py"), "w") as ofp:
            ofp.write("raise RuntimeError('foo')\n")
        with self.assertRaises(RuntimeError):
            adapters.load(path=self.test_dir, skip_failures=False)

    def test_08(self):
        "test call get() and names() before load()"
        self.assertFalse(adapters.__adapters__)
        self.assertIsNone(adapters.get("test"))
        self.assertFalse(adapters.names())
