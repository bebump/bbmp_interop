'''
Copyright (c) 2020 Attila Szarvas <attila.szarvas@gmail.com>

All rights reserved. Use of this source code is governed the 3-Clause BSD
License BSD-style license that can be found in the LICENSE file.
'''

import logging
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

import bbmp_subprocess
import bbmp_util as util

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def rel_to_py(*paths):
    return os.path.join(os.path.realpath(os.path.dirname(__file__)), *paths)


PROJECT_DIR = rel_to_py("..")

VCVARSALL_COMMAND = []
PLATFORM_SPECIFIC_CMAKE_PARAMETERS = []

if sys.platform == "win32":
    vcvarsall = util.get_most_recent_file(
        util.find_file(
            "vcvarsall.bat",
            root="C:\\",
            search_constraint=["Program Files", "Visual Studio"],
            cache_result=False,
        )
    )
    assert vcvarsall, "vcvarsall.bat not found"

    VCVARSALL_COMMAND = [vcvarsall, "x86_amd64"]
    PLATFORM_SPECIFIC_CMAKE_PARAMETERS = ["-G", "NMake Makefiles"]


def run_ctests():
    with tempfile.TemporaryDirectory() as cmake_build_dir:
        commands = [
            VCVARSALL_COMMAND,
            [
                "cmake",
                "-S",
                PROJECT_DIR,
                "-B",
                cmake_build_dir,
                *PLATFORM_SPECIFIC_CMAKE_PARAMETERS,  # selects generator on Windows
            ],
            [
                "cmake",
                "--build",
                cmake_build_dir,
                "--target",
                "test",
                "--",
                'ARGS="--verbose"',
            ],
        ]
        bbmp_subprocess.run_in_shell(commands)


def install(build_dir, cmake_install_prefix):
    commands = [
        VCVARSALL_COMMAND,
        [
            "cmake",
            "-S",
            PROJECT_DIR,
            "-B",
            build_dir,
            f"-DCMAKE_INSTALL_PREFIX={cmake_install_prefix}",
            *PLATFORM_SPECIFIC_CMAKE_PARAMETERS,
        ],
        ["cmake", "--build", build_dir, "--target", "install"],
    ]
    bbmp_subprocess.run_in_shell(commands)


def _run_ctests():
    with tempfile.TemporaryDirectory() as cmake_build_dir:
        bbmp_subprocess.run_in_shell(
            [
                ["cmake", "-S", PROJECT_DIR, "-B", cmake_build_dir,],
                [
                    "cmake",
                    "--build",
                    cmake_build_dir,
                    "--target",
                    "test",
                    "--",
                    'ARGS="--verbose"',
                ],
            ]
        )


TEST_CPP_CONTENT = """
#include "bbmp_interop/types.hpp"

#define EXPORT_TO_PYTHON

EXPORT_TO_PYTHON
int eight() { return 8; }
"""


def create_project_using_installed_bbmp_interop(source_dir):
    test_CMakeLists_txt_content = """
cmake_minimum_required(VERSION 3.15)

project(import_bbmp_interop)

find_package(bbmp_interop 0.1 REQUIRED)

add_library(hello STATIC test.cpp)
target_link_libraries(hello PRIVATE bbmp::bbmp_types)

bbmp_add_python_module(pyhello LINK_LIBRARIES hello)
"""

    with open(os.path.join(source_dir, "CMakeLists.txt"), "w") as file:
        file.write(test_CMakeLists_txt_content)

    with open(os.path.join(source_dir, "test.cpp"), "w") as file:
        file.write(TEST_CPP_CONTENT)


def create_project_using_subdirectory_bbmp_interop(source_dir):
    test_CMakeLists_txt_content = """
cmake_minimum_required(VERSION 3.15)

project(import_bbmp_interop)

add_subdirectory(extern/bbmp_interop)

add_library(hello STATIC test.cpp)
target_link_libraries(hello PRIVATE bbmp_types)

bbmp_add_python_module(pyhello LINK_LIBRARIES hello)
"""

    with open(os.path.join(source_dir, "CMakeLists.txt"), "w") as file:
        file.write(test_CMakeLists_txt_content)

    with open(os.path.join(source_dir, "test.cpp"), "w") as file:
        file.write(TEST_CPP_CONTENT)


def as_posix(path):
    return pathlib.PurePath(path).as_posix()


class TestUsage(unittest.TestCase):
    def test_installed_library(self):
        with tempfile.TemporaryDirectory() as bbmp_interop_build_dir:
            with tempfile.TemporaryDirectory() as cmake_install_prefix:
                install(bbmp_interop_build_dir, cmake_install_prefix)

                with tempfile.TemporaryDirectory() as importing_lib_dir:
                    create_project_using_installed_bbmp_interop(importing_lib_dir)
                    build_dir = os.path.join(importing_lib_dir, "build")
                    commands = [
                        VCVARSALL_COMMAND,
                        [
                            "cmake",
                            "-S",
                            importing_lib_dir,
                            "-B",
                            build_dir,
                            f"-DCMAKE_PREFIX_PATH={cmake_install_prefix}",
                            *PLATFORM_SPECIFIC_CMAKE_PARAMETERS,
                        ],
                        ["cmake", "--build", build_dir],
                    ]
                    bbmp_subprocess.run_in_shell(commands)

                    # We need to run this in a subprocess, because you can't unload a module (DLL), so if
                    # this process loaded the extension, the TMP directories couldn't be cleaned up
                    native_module_test_command = [
                        sys.executable,
                        "-c",
                        f"import sys;sys.path.append('{as_posix(build_dir)}');import pyhello;assert pyhello.eight() == 8",
                    ]
                    bbmp_subprocess.run_in_shell([native_module_test_command])

    def test_using_as_subdir(self):
        with tempfile.TemporaryDirectory() as importing_lib_dir:
            create_project_using_subdirectory_bbmp_interop(importing_lib_dir)
            items_to_copy = [
                os.path.join(PROJECT_DIR, "cmake"),
                os.path.join(PROJECT_DIR, "extern"),
                os.path.join(PROJECT_DIR, "src"),
                os.path.join(PROJECT_DIR, "tests"),
                os.path.join(PROJECT_DIR, ".clang-format"),
                os.path.join(PROJECT_DIR, ".gitignore"),
                os.path.join(PROJECT_DIR, "bbmp_interop-config.cmake.in"),
                os.path.join(PROJECT_DIR, "CMakeLists.txt"),
                os.path.join(PROJECT_DIR, "README.md"),
            ]
            subdir_path = os.path.join(importing_lib_dir, "extern", "bbmp_interop")
            pathlib.Path(subdir_path).mkdir(parents=True, exist_ok=True)
            for item in items_to_copy:
                if os.path.isdir(item):
                    shutil.copytree(
                        item, os.path.join(subdir_path, pathlib.PurePath(item).name)
                    )
                else:
                    shutil.copy2(item, subdir_path)
            build_dir = os.path.join(importing_lib_dir, "build")
            commands = [
                VCVARSALL_COMMAND,
                [
                    "cmake",
                    "-S",
                    importing_lib_dir,
                    "-B",
                    build_dir,
                    *PLATFORM_SPECIFIC_CMAKE_PARAMETERS,
                ],
                ["cmake", "--build", build_dir],
            ]
            bbmp_subprocess.run_in_shell(commands)

            # We need to run this in a subprocess, because you can't unload a module (DLL), so if
            # this process loaded the extension, the TMP directories couldn't be cleaned up
            native_module_test_command = [
                sys.executable,
                "-c",
                f"import sys;sys.path.append('{as_posix(build_dir)}');import pyhello;assert pyhello.eight() == 8",
            ]
            bbmp_subprocess.run_in_shell([native_module_test_command])


if __name__ == "__main__":
    logging.basicConfig(format="%(message)s")
    unittest.main()
