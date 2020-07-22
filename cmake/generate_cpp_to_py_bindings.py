'''
Copyright (c) 2020 Attila Szarvas <attila.szarvas@gmail.com>

All rights reserved. Use of this source code is governed the 3-Clause BSD
License BSD-style license that can be found in the LICENSE file.
'''

import logging
import os
import pathlib
import pickle
import re
from string import Template
from typing import Any, Dict, List, Optional, TextIO, Tuple, Union

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


NAME_OF_THIS_FILE = pathlib.PurePath(__file__).name
CHANGES_CACHE_PATH = os.path.join(os.getcwd(), f".tmp.{NAME_OF_THIS_FILE}.cache")
INTERMEDIATE_CACHE_PATH = os.path.join(
    os.getcwd(), f"{NAME_OF_THIS_FILE}.intermediate.cache"
)
EXPORT_ANNOTATION = "EXPORT_TO_PYTHON"


def cpp_indent(code, spaces):
    indented_code = ""

    level = 0
    for line in code.splitlines():
        if "}" not in line:
            indented_code += f'{"".join([" "] * level * spaces)}{line}\n'

        if "{" in line:
            level += 1

        if "}" in line:
            level -= 1

        if "}" in line:
            indented_code += f'{"".join([" "] * level * spaces)}{line}\n'

    return indented_code


def load_json_maybe(path):
    try:
        with open(path, "rb") as cache_file:
            return pickle.load(cache_file)
    except:
        return {}


class ChangesCache:
    def __init__(self, path):
        self.path = path
        self.cache: Dict[str, Any] = load_json_maybe(path)

    def erase(self):
        self.cache = {}

    def get_changed_file_paths(self, file_paths: List[str]):
        changed_file_paths = []
        for f in file_paths:
            file_modified = True

            try:
                if self.cache[f]["last_modification_time"] == os.path.getmtime(f):
                    file_modified = False
            except:
                pass

            if file_modified:
                changed_file_paths.append(f)

        return changed_file_paths

    def update_modification_time(self, path):
        if path not in self.cache.keys():
            self.cache[path] = {}
        self.cache[path]["last_modification_time"] = os.path.getmtime(path)

    def store_data(self, path, data):
        if path not in self.cache.keys():
            self.cache[path] = {}
        self.cache[path]["data"] = data

    def get_data(self, path):
        data = None
        try:
            data = self.cache[path]["data"]
        except:
            pass

        return data

    def exists_unchanged(self, path):
        try:
            if self.cache[path]["last_modification_time"] == os.path.getmtime(path):
                return True
        except:
            pass

        return False

    def save_to_disk(self):
        logger.debug(
            f"{NAME_OF_THIS_FILE}: saving file modification dates to {self.path}"
        )
        with open(self.path, "wb") as file:
            pickle.dump(self.cache, file)


class FunctionSignature:
    def __init__(self, signature_str: str, namespace: Optional[str] = None):
        self.return_type: str = None
        self.name: str = None
        self.namespace = namespace
        self.parameters: Tuple[str, str] = []
        self.specifiers: List[str] = []

        return_type_and_name, _, rest = signature_str.partition("(")
        return_type_and_name_tokens = return_type_and_name.split()
        self.return_type = " ".join(return_type_and_name_tokens[:-1])
        self.name = return_type_and_name_tokens[-1]
        parameters_string, _, decorators = rest.partition(")")
        for type_and_maybe_name_str in parameters_string.split(","):
            base_type_and_maybe_name = (
                type_and_maybe_name_str.replace("const", "")
                .replace("*", "")
                .replace("&", "")
                .split()
            )
            name = None
            if len(base_type_and_maybe_name) > 1:
                name = base_type_and_maybe_name[1].strip()
            type = (
                " ".join(
                    [
                        type_token.strip()
                        for type_token in type_and_maybe_name_str.split()[:-1]
                    ]
                )
                if name is not None
                else type_and_maybe_name_str.strip()
            )
            self.parameters.append((type, name))

        self.specifiers = decorators.split()

    def get_signature(self):
        def get_parameter_str(p: Tuple[str, Optional[str]]):
            return f"{p[0]} {p[1]}" if p[1] else p[0]

        return f"{self.return_type} {self.name}({', '.join([get_parameter_str(p) for p in self.parameters])}) {' '.join(self.specifiers)}".strip()

    def get_fully_qualified_name(self):
        if self.namespace is None:
            return self.name

        return f"{self.namespace}::{self.name}"


NAMESPACE_REGEX = re.compile(
    r"(?:^|\s)(?:namespace|class|struct)\s*([a-zA-Z0-9\-\_]+)\s*{"
)


def extract_function_signatures_from_cpp(
    file_or_lines_of_code: Union[TextIO, List[str]],
) -> List[Tuple[Optional[str], str]]:
    code = ""

    # Getting rid of compiler directives and // comments
    for line in file_or_lines_of_code:
        line = line.strip()
        if len(line) > 0 and line[0] == "#":
            continue
        code += line.split("//")[0] + " "

    # Getting rid of /* */ comments
    while True:
        comment_start = code.find("/*")
        if comment_start == -1:
            break
        comment_end = code.find("*/", comment_start + 2)
        if comment_end == -1:
            break
        code = code[:comment_start] + code[comment_end + 2 :]

    def decompose_into_namespaces(code_by_namespace: Dict[str, str], signatures=[]):
        def extend_namespace(n1, n2):
            if n1 is None:
                return n2
            return f"{n1}::{n2}"

        next_code_by_namespace = {}
        for current_namespace, code in code_by_namespace.items():
            while True:
                namespace_match = NAMESPACE_REGEX.search(code)
                if namespace_match is None:
                    break

                namespace = namespace_match.groups()[0]
                match_start = namespace_match.span()[0]
                start = namespace_match.span()[1]
                cursor = start

                depth = 1
                while True:
                    if code[cursor] == "}":
                        depth -= 1
                    elif code[cursor] == "{":
                        depth += 1

                    if depth == 0:
                        end = cursor
                        break

                    cursor += 1

                next_code_by_namespace[
                    extend_namespace(current_namespace, namespace)
                ] = code[start:end]
                code = code[:match_start] + code[end + 1 :]

            signatures.append((current_namespace, code))

        if len(next_code_by_namespace) == 0:
            return signatures

        return decompose_into_namespaces(next_code_by_namespace, signatures)

    code_by_namespace = decompose_into_namespaces({None: code})

    functions: List[Tuple[Optional[str], str]] = []
    for namespace, code in code_by_namespace:
        cursor = 0
        while True:
            annotation_start = code.find(EXPORT_ANNOTATION, cursor)
            if annotation_start == -1:
                break

            start = annotation_start + len(EXPORT_ANNOTATION)
            first_bracket = code.find("{", start)
            first_semicolon = code.find(";", start)
            end = None
            if first_bracket == -1:
                end = first_semicolon
            elif first_semicolon == -1:
                end = first_bracket
            else:
                end = min(first_semicolon, first_bracket)

            signature = code[start:end].strip()
            functions.append((signature, namespace))

            cursor = end + 1

    return functions


def get_pybind11_arg_code(function_signature: FunctionSignature) -> List[str]:
    """
    Parameter names are only added, if they are available. Since the function we are exporting could be just a
    declaration containing only types, they are not necessarily available.
    """
    parameter_names = []
    if all([p[1] is not None for p in function_signature.parameters]):
        parameter_names = [
            f'pybind11::arg("{p[1]}")' for p in function_signature.parameters
        ]

    return parameter_names


TYPE_PARAMETER_REGEX = re.compile(r"<([a-zA-Z0-9\s\-\_]+)>")


def create_wrapper_function_code(
    function_signature: FunctionSignature,
) -> Optional[Tuple[str, str]]:
    """Functions that have bbmp::OwnedChannelData parameter require a wrapper, transforming from `pybind11::array_t`
       to `bbmp::OwnedChannelData`, which erase the underlying type. Thus, the exported function need not depend
       on `numpy.h`.

       Returns a tuple(name_of_wrapper_function, definition_of_wrapper_function).
    """
    if not any(
        [
            "bbmp::OwnedChannelData" in param[0]
            for param in function_signature.parameters
        ]
    ):
        return None

    wrapper_parameters = []
    arg_counter = 0
    for param in function_signature.parameters:
        if "bbmp::OwnedChannelData" in param[0]:
            type_specialization = TYPE_PARAMETER_REGEX.search(param[0]).groups()[0]
            param_type = f"pybind11::array_t<{type_specialization}, 0>"
            param_name = param[1] if len(param) > 1 else f"arg{arg_counter}"
            arg_counter += 1
            wrapper_parameters.append((param_type, param_name))
        else:
            wrapper_parameters.append(param)
    array_checks = [
        f"assert_c_contiguous({pname});"
        for ptype, pname in wrapper_parameters
        if "array_t" in ptype
    ]

    wrapper_body = []
    variable_wrappers = []
    forwarded_parameters = []

    for (_, param_name), (original_type, _) in zip(
        wrapper_parameters, function_signature.parameters
    ):
        is_lvalue_ref = (
            "&" in original_type
            and not "&&" in original_type
            and not "const" in original_type
        )
        is_const_lvalue_ref = (
            "&" in original_type
            and not "&&" in original_type
            and "const" in original_type
        )
        is_rvalue_ref = "&&" in original_type and not "const" in original_type
        is_const_rvalue_ref = "&&" in original_type and not "const" in original_type

        if "bbmp::OwnedChannelData" in original_type:
            type_specialization = TYPE_PARAMETER_REGEX.search(original_type).groups()[0]
            variable_wrappers.append(
                f"auto {param_name}_wrapper = bbmp::createOwnedChannelData(std::move({param_name}));"
            )
            forwarded_name = f"{param_name}_wrapper"
        else:
            forwarded_name = f"{param_name}"

        # Only a non-const lvalue reference can't bind to an rvalue.
        if is_lvalue_ref:
            forwarded_parameters.append(forwarded_name)
        else:
            forwarded_parameters.append(f"std::move({forwarded_name})")

    wrapper_body += variable_wrappers
    wrapper_body += forwarded_parameters

    wrapper_name = (
        f"{function_signature.get_fully_qualified_name().replace('::', '__')}_wrapper"
    )
    wrapper_body = Template(
        """$descriptor_return_type $wrapper_name($parameters)
{
$array_checks
$variable_wrappers
$forwarding_call
}"""
    ).substitute(
        descriptor_return_type=function_signature.return_type,
        wrapper_name=wrapper_name,
        parameters=", ".join(
            [f"{ptype} {pname}" for ptype, pname in wrapper_parameters]
        ),
        array_checks=os.linesep.join(array_checks),
        variable_wrappers=os.linesep.join(variable_wrappers),
        forwarding_call=f"return {function_signature.get_fully_qualified_name()}({', '.join(forwarded_parameters)});",
    )
    return wrapper_name, wrapper_body


class CodeSections:
    def __init__(self):
        self.function_signatures = []
        self.function_declarations = []
        self.wrapper_definitions = []
        self.module_function_definitions = []

    def append(self, code_sections):
        other_dict = {}

        if isinstance(code_sections, dict):
            other_dict = code_sections
        elif isinstance(code_sections, CodeSections):
            other_dict = code_sections.__dict__
        else:
            assert (
                False
            ), "CodeSections.append() takes 1 parameter of either CodeSections or dict"

        assert (
            self.__dict__.keys() == other_dict.keys()
        ), "CodeSections.append() got parameter with wrong keys"

        for k, v in other_dict.items():
            self.__dict__[k] += v


def generate_code_sections(function_signature: FunctionSignature):
    function_declaration = f"extern {function_signature.get_signature()};"
    if function_signature.namespace is not None:
        namespaces = function_signature.namespace.split("::")
        namespaces.reverse()
        for namespace in namespaces:
            brl = "{"
            brr = "}"
            function_declaration = (
                f"namespace {namespace} {brl} {function_declaration} {brr}"
            )
    function_declarations = [function_declaration]

    wrapper_definitions = []
    module_function_definitions = []

    add_quotes = lambda s: f'"{s}"'

    wrapper_defintion = create_wrapper_function_code(function_signature)
    wrapper_definitions = (
        [wrapper_defintion[1]] if wrapper_defintion is not None else []
    )

    if wrapper_defintion is not None:
        module_function_definitions.append(
            f'm.def({", ".join([add_quotes(function_signature.get_fully_qualified_name().replace("::", "__")), f"&{wrapper_defintion[0]}"] + get_pybind11_arg_code(function_signature))});'
        )
    else:
        module_function_definitions.append(
            f'm.def({", ".join([add_quotes(function_signature.get_fully_qualified_name().replace("::", "__")), f"&{function_signature.get_fully_qualified_name()}"] + get_pybind11_arg_code(function_signature))});'
        )

    code_sections = CodeSections()
    code_sections.function_signatures = [
        (function_signature.get_signature(), function_signature.namespace)
    ]
    code_sections.function_declarations = function_declarations
    code_sections.module_function_definitions = module_function_definitions
    code_sections.wrapper_definitions = wrapper_definitions

    return code_sections


def generate_cpp(code_sections: CodeSections, module_name: str):
    includes = ['#include "pybind11/pybind11.h"']

    # Wrappers are created for `bbmp::OwnedChannelData` parameters.
    # Thus, if we have wrappers, we need to include `types.hpp` and
    # `conversions.hpp`
    if code_sections.wrapper_definitions:
        includes = ['#include "bbmp_interop/types.hpp"', '#include "bbmp_interop/conversions.hpp"', ""] + includes

    code: str = Template(
        """/* THIS FILE IS AUTO GENERATED BY BBMP_INTEROP */

$includes

$function_declarations

$wrapper_definitions

PYBIND11_MODULE($module_name, m) {
$module_function_definitions
}"""
    ).substitute(
        includes=os.linesep.join(includes),
        module_name=module_name,
        function_declarations=os.linesep.join(code_sections.function_declarations),
        wrapper_definitions=os.linesep.join(code_sections.wrapper_definitions),
        module_function_definitions=os.linesep.join(
            code_sections.module_function_definitions
        ),
    )

    return code


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--sources", type=str, required=True)
    parser.add_argument("--module_name", type=str, required=True)
    args = parser.parse_args()

    sources = args.sources.split(";")
    changes_cache = ChangesCache(CHANGES_CACHE_PATH)

    this_generator_script_path = pathlib.PurePath(os.path.realpath(__file__)).as_posix()
    if not changes_cache.exists_unchanged(this_generator_script_path):
        changes_cache.erase()
        changes_cache.update_modification_time(this_generator_script_path)

    # Erase cache contents about paths that are no longer part of the build.
    # This means that if you build multiple targets in a single build
    # directory, subsequent calls to the generator may erase each other's
    # cached information. So I'm considering removing this.
    old_paths = [
        k
        for k in list(changes_cache.cache.keys())
        if k not in sources + [this_generator_script_path, args.output]
    ]
    for path in old_paths:
        print(f"deleting {path}")
        del changes_cache.cache[path]

    # This signals whether the output file has to be regenerated. It only
    # needs to be regenerated if any of the function signatures in any of the
    # source files changed.
    inputs_changed = False
    for path in sources:
        if not changes_cache.exists_unchanged(path):
            fsigs = []
            with open(path, "r") as file:
                fsigs = extract_function_signatures_from_cpp(file)
            cached_code_sections = changes_cache.get_data(path)
            if cached_code_sections is None or not set(
                cached_code_sections["function_signatures"]
            ) == set(fsigs):
                source_code_sections = CodeSections()
                for signature, namespace in fsigs:
                    source_code_sections.append(
                        generate_code_sections(FunctionSignature(signature, namespace))
                    )
                changes_cache.update_modification_time(path)
                changes_cache.store_data(path, source_code_sections.__dict__)
                inputs_changed = True

    output_changed = not changes_cache.exists_unchanged(args.output)

    if inputs_changed or output_changed:
        code_sections = CodeSections()
        for path in sources:
            code_sections.append(changes_cache.get_data(path))

        code = generate_cpp(code_sections, args.module_name)
        code = cpp_indent(code, 2)

        with open(args.output, "w") as output_file:
            output_file.write(code)
            changes_cache.update_modification_time(args.output)

        changes_cache.save_to_disk()
    else:
        logger.info(
            f"{NAME_OF_THIS_FILE}: no changes in exported function signatures. Skipping code generation."
        )


if __name__ == "__main__":
    logging.basicConfig()
    import time

    start = time.perf_counter()
    main()
    end = time.perf_counter()
    logger.info(f"{NAME_OF_THIS_FILE}: code generation took {end - start:.2f} s")
