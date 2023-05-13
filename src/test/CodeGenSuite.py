import unittest
from TestUtils import TestCodeGen
from AST import *


class CheckCodeGenSuite(unittest.TestCase):
    def test_simple_program(self):
        """Simple program"""
        input = """main: function void () {
        }"""
        expect = """"""
        self.assertTrue(TestCodeGen.test(input, expect, 500))
