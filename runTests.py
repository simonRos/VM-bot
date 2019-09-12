#!/usr/bin/env python3
import unittest
from vagrant_api_tests import *

def test_suite():
    suite = unittest.TestSuite()
    results = unittest.TestResult()
    #Do this for each test class
    #suite.addTest(unittest.makeSuite(TEST))
    suite.addTest(unittest.makeSuite(TestAdminChecks))
    #suite.addTest(unittest.makeSuite(TestBuild))
    suite.addTest(unittest.makeSuite(TestClaims))
    #suite.addTest(unittest.makeSuite(TestClean))
    suite.addTest(unittest.makeSuite(TestIdentity))
    suite.addTest(unittest.makeSuite(TestLogging))
    suite.addTest(unittest.makeSuite(TestSecurity))
    suite.addTest(unittest.makeSuite(TestUtilities))
    runner = unittest.TextTestRunner()
    print(runner.run(suite))

test_suite()
