'''
Copyright (c) 2020 Attila Szarvas <attila.szarvas@gmail.com>

All rights reserved. Use of this source code is governed the 3-Clause BSD
License BSD-style license that can be found in the LICENSE file.
'''

import sys
import os
import unittest


def rel_to_py(*paths):
    return os.path.join(os.path.realpath(os.path.dirname(__file__)), *paths)


sys.path.append(rel_to_py("..", "cmake"))
import generate_cpp_to_py_bindings as generator


class TestFunctionSignatureParsing(unittest.TestCase):
    def setUp(self):
        self.signature1 = generator.FunctionSignature(
            "const std::string test_function(int*, const std::string& s) noexcept"
        )
        self.signature2 = generator.FunctionSignature(
            "std::string test_function(int num, const std::string& s) const noexcept"
        )
        self.signature3 = generator.FunctionSignature(
            "std::string& funcNotConstNoexcept(int, const std::string&&)"
        )

    def test_return_type(self):
        self.assertEqual("const std::string", self.signature1.return_type)
        self.assertEqual("std::string", self.signature2.return_type)
        self.assertEqual("std::string&", self.signature3.return_type)

    def test_name(self):
        self.assertEqual("test_function", self.signature1.name)
        self.assertEqual("test_function", self.signature2.name)
        self.assertEqual("funcNotConstNoexcept", self.signature3.name)

    def test_parameter_types(self):
        self.assertEqual(
            ["int*", "const std::string&"], [t for t, n in self.signature1.parameters]
        )
        self.assertEqual(
            ["int", "const std::string&"], [t for t, n in self.signature2.parameters]
        )
        self.assertEqual(
            ["int", "const std::string&&"], [t for t, n in self.signature3.parameters]
        )

    def test_parameter_names(self):
        self.assertEqual([None, "s"], [n for t, n in self.signature1.parameters])
        self.assertEqual(["num", "s"], [n for t, n in self.signature2.parameters])
        self.assertEqual([None, None], [n for t, n in self.signature3.parameters])

    def test_specifiers(self):
        self.assertEqual(["noexcept"], self.signature1.specifiers)
        self.assertEqual(["const", "noexcept"], self.signature2.specifiers)
        self.assertEqual([], self.signature3.specifiers)


class TestCodeParsing(unittest.TestCase):
    def setUp(self):
        code = """
#include "types.hpp"

#define EXPORT_TO_PYTHON

EXPORT_TO_PYTHON
void multiplyValues(bbmp::OwnedChannelData<float> data,
                    const float multiplier) noexcept {
  for (int chIx = 0; chIx < data.num_channels(); ++chIx) {
    auto ptr = data.GetWriteChannelPtr(chIx);
    for (size_t i = 0; i < data.length(); ++i) *(ptr + i) *= multiplier;
  }
}

EXPORT_TO_PYTHON
std::string hello() { return "Hello from C++"; }

void not_exported() {}

EXPORT_TO_PYTHON
// Trying to trip up the parser
const int tricky_namespace_const_function_namespace() { return 0; }

namespace test_namespace {
EXPORT_TO_PYTHON
void add_to_array(bbmp::OwnedChannelData<float>& data, const float number) {
  for (int chIx = 0; chIx < data.num_channels(); ++chIx) {
    auto ptr = data.GetWriteChannelPtr(chIx);
    for (size_t i = 0; i < data.length(); ++i) *(ptr + i) += number;
  }

  namespace embedded_namespace {
  EXPORT_TO_PYTHON
  void function_in_embedded_namespace() {}
  }  // namespace embedded_namespace
}
}  // namespace test_namespace
"""
        self.function_signature_tuples = generator.extract_function_signatures_from_cpp(
            code.splitlines()
        )
        self.function_signatures_set = set(self.function_signature_tuples)

    def test_correct_number_of_functions_extracted(self):
        self.assertEqual(5, len(self.function_signature_tuples))

    def test_functions_outside_namespaces(self):
        self.assertIn(
            ("void multiplyValues(bbmp::OwnedChannelData<float> data, const float multiplier) noexcept", None),
            self.function_signatures_set
        )

        self.assertIn(
            ("std::string hello()", None),
            self.function_signatures_set
        )

        self.assertIn(
            ("const int tricky_namespace_const_function_namespace()", None),
            self.function_signatures_set
        )

    def test_non_exported_function_not_extracted(self):
        self.assertNotIn(
            ("void not_exported()", None),
            self.function_signatures_set
        )

    def test_extracting_function_in_namespace(self):
        self.assertIn(
            ("void add_to_array(bbmp::OwnedChannelData<float>& data, const float number)", "test_namespace"),
            self.function_signatures_set
        )

    def test_extracting_function_in_multiple_namespaces(self):
        self.assertIn(
            ("void function_in_embedded_namespace()", "test_namespace::embedded_namespace"),
            self.function_signatures_set
        )

if __name__ == "__main__":
    unittest.main()
