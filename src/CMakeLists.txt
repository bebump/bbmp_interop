# Copyright (c) 2020 Attila Szarvas <attila.szarvas@gmail.com>
#
# All rights reserved. Use of this source code is governed the 3-Clause BSD
# License BSD-style license that can be found in the LICENSE file.

#[===========================================================================[
Usage:
  Exported targets: `bbmp-types` (header only, no additional dependencies)
#]===========================================================================]

cmake_minimum_required(VERSION 3.12)

set(BBMP_TYPES_TARGET_NAME bbmp_types)
add_library(${BBMP_TYPES_TARGET_NAME} INTERFACE)
set_target_properties(${BBMP_TYPES_TARGET_NAME}
                      PROPERTIES PUBLIC_HEADER bbmp_interop/types.hpp)

include(GNUInstallDirs)

target_include_directories(
  ${BBMP_TYPES_TARGET_NAME}
  INTERFACE $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
            $<BUILD_INTERFACE:${CMAKE_CURRENT_LIST_DIR}>)

# =============================================================================
# INSTALL
# =============================================================================

install(
  TARGETS ${BBMP_TYPES_TARGET_NAME}
  EXPORT ${BBMP_TYPES_TARGET_NAME}-targets
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR} # This one has no effect when
          # installing a .lib on Windows.
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR} # A .lib on Windows is considered
          # an ARCHIVE, so this matters
  PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/bbmp_interop)

set(SCRIPT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../cmake")
install(FILES "${SCRIPT_DIR}/bbmp_interop_tools.cmake"
              "${SCRIPT_DIR}/generate_cpp_to_py_bindings.py"
        DESTINATION lib/cmake/bbmp_interop)

install(FILES "bbmp_interop/conversions.hpp"
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/bbmp_interop)

install(
  EXPORT ${BBMP_TYPES_TARGET_NAME}-targets
  FILE ${BBMP_TYPES_TARGET_NAME}-targets.cmake
  NAMESPACE bbmp::
  DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/bbmp_interop)

# =============================================================================
