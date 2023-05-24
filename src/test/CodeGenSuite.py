import unittest
from TestUtils import TestCodeGen
from AST import *


class CheckCodeGenSuite(unittest.TestCase):
    # def test_simple_program(self):
    #     """Simple program"""
    #     input = """main: function void () {
    #         a : integer = 4;
    #         printInteger(a);
    #     }"""
    #     expect = """"""
    #     self.assertTrue(TestCodeGen.test(input, expect, 500))
    def test_simple_program1(self):
        """Simple program"""
        input = """
        c : integer = 1;
        main: function void () {
            b : integer = 4;
            a : array[2,3] of integer;
            a[1,2] = 2;
        }"""
        expect = """"""
        self.assertTrue(TestCodeGen.test(input, expect, 501))
