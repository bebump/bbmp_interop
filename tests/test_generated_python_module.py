'''
Copyright (c) 2020 Attila Szarvas <attila.szarvas@gmail.com>

All rights reserved. Use of this source code is governed the 3-Clause BSD
License BSD-style license that can be found in the LICENSE file.
'''

import inspect
import logging
import os
import pathlib
import sys
import unittest

import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_member_functions(module):
    function_signatures = []
    for member in inspect.getmembers(module):
        if not member[0].startswith("__"):
            function_signatures.append(member[1].__doc__.strip())
    return function_signatures


class TestNonNumpyFunctions(unittest.TestCase):
    def test_function_returning_std_string(self):
        self.assertEqual("Hello from C++", pybbmp_interop_test.hello())


class TestNumpyFunctions(unittest.TestCase):
    def test_function_should_throw_for_bad_type(self):
        x = np.ones((4, 10)).astype(np.float)
        with self.assertRaises(TypeError):
            pybbmp_interop_test.multiplyValues(x, 2.0)

    def test_numpy_function(self):
        expected = np.ones((4, 10)).astype(np.float32) * 2.0
        actual = np.ones((4, 10)).astype(np.float32)
        pybbmp_interop_test.multiplyValues(actual, 2.0)
        self.assertTrue(np.allclose(expected, actual))

    def test_numpy_function_in_namespace(self):
        expected = np.ones((4, 10)).astype(np.float32) + 1.2
        actual = np.ones((4, 10)).astype(np.float32)
        pybbmp_interop_test.test_namespace__add_to_array(actual, 1.2)
        self.assertTrue(np.allclose(expected, actual))


if __name__ == "__main__":
    logging.basicConfig()
    if len(sys.argv) < 2:
        logger.fatal(
            """You must specify the path in which the compiled pybbmp_interop_test
module can be found. Using ctest instead of running this function directly will
specify that directory"""
        )
        exit(-1)

    module_path = pathlib.PurePath(sys.argv[1])
    if os.path.isdir(module_path):
        sys.path.append(str(module_path))
    else:
        sys.path.append(str(module_path.parent))

    sys.argv = sys.argv[:1]
    import pybbmp_interop_test

    print("Functions available in module pybbmp_interop_test:")
    for fs in get_member_functions(pybbmp_interop_test):
        print(f"  {fs}")

    unittest.main()
