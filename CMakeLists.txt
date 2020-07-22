# Copyright (c) 2020 Attila Szarvas <attila.szarvas@gmail.com>
#
# All rights reserved. Use of this source code is governed the 3-Clause BSD
# License BSD-style license that can be found in the LICENSE file.

cmake_minimum_required(VERSION 3.12)

project(
  bbmp_interop
  VERSION 0.1.0
  DESCRIPTION "Library for autogenerating Python extension modules"
  LANGUAGES C CXX)

set(LIB_NAME bbmp_interop)

add_subdirectory(src)
include(cmake/bbmp_interop_tools.cmake)

# =============================================================================
# INSTALL
# =============================================================================

install(DIRECTORY extern DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/bbmp_interop)

set(PYBIND11_INCLUDE_DIR
    ${CMAKE_INSTALL_INCLUDEDIR}/bbmp_interop/extern/pybind11/include)

include(CMakePackageConfigHelpers)
configure_package_config_file(
  ${LIB_NAME}-config.cmake.in
  "${CMAKE_CURRENT_BINARY_DIR}/${LIB_NAME}-config.cmake"
  INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/${LIB_NAME}
  PATH_VARS PYBIND11_INCLUDE_DIR)

write_basic_package_version_file(
  ${LIB_NAME}-config-version.cmake
  VERSION ${bbmp_interop_VERSION}
  COMPATIBILITY SameMajorVersion)

include(GNUInstallDirs)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/${LIB_NAME}-config.cmake"
              "${CMAKE_CURRENT_BINARY_DIR}/${LIB_NAME}-config-version.cmake"
        DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/${LIB_NAME})

# =============================================================================
# TEST
# =============================================================================

set(BBMP_INTEROP_MASTER_PROJECT OFF)
if(CMAKE_CURRENT_SOURCE_DIR STREQUAL CMAKE_SOURCE_DIR)
  set(BBMP_INTEROP_MASTER_PROJECT ON)
endif()

option(BUILD_TESTING "Build bbmp_interop tests?" ${BBMP_INTEROP_MASTER_PROJECT})

if(BUILD_TESTING)
  add_subdirectory(tests)

  find_package(Python ${Python_VERSION} REQUIRED COMPONENTS Interpreter)
  enable_testing()
  add_test(NAME cpp_parsing_test
           COMMAND "${Python_EXECUTABLE}"
                   "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_generator.py")
  add_test(NAME build_test_module
           COMMAND "${CMAKE_COMMAND}" --build "${CMAKE_BINARY_DIR}" --config
                   "$<CONFIG>" --target pybbmp_interop_test)
  add_test(
    NAME generated_py_module_test
    COMMAND
      "${Python_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_generated_python_module.py"
      "$<TARGET_FILE:pybbmp_interop_test>")
  add_test(
    NAME including_the_library_test
    COMMAND
      "${Python_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_export_import.py")

  set_tests_properties(generated_py_module_test PROPERTIES FIXTURES_REQUIRED
                                                           build_test_binaries)
  set_tests_properties(including_the_library_test
                       PROPERTIES FIXTURES_REQUIRED build_test_binaries)
  set_tests_properties(build_test_module PROPERTIES FIXTURES_SETUP
                                                    build_test_binaries)

endif()
