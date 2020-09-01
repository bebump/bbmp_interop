# Copyright (c) 2020 Attila Szarvas <attila.szarvas@gmail.com>
#
# All rights reserved. Use of this source code is governed the 3-Clause BSD
# License BSD-style license that can be found in the LICENSE file.

set(BBMP_INTEROP_TOOLS_PATH
    ${CMAKE_CURRENT_LIST_DIR}
    CACHE INTERNAL "")

macro(SETUP_VARIABLES)
  set(BBMP_CONVERSIONS_TARGET_NAME "bbmp_python_conversion")

  if(NOT BBMP_INTEROP_INSTALLED)
    set(PYBIND11_INCLUDE_DIR
        "${BBMP_INTEROP_TOOLS_PATH}/../extern/pybind11/include")
    set(BBMP_TYPES_TARGET_NAME bbmp_types)
  else()
    set(BBMP_TYPES_TARGET_NAME bbmp::bbmp_types)
  endif()
endmacro()

function(CREATE_BBMP_PYTHON_CONVERSIONS_TARGET)
  setup_variables()

  if(Python_ROOT_DIR)
    set(Python_FIND_STRATEGY LOCATION)
  else()
    set(Python_FIND_STRATEGY VERSION)
  endif()
  find_package(Python ${Python_VERSION} REQUIRED COMPONENTS Interpreter
                                                            Development NumPy)

  message(STATUS "bbmp_interop is linking to the Python environment belonging to ${Python_EXECUTABLE}")

  add_library(extern_pybind11 INTERFACE)
  target_include_directories(extern_pybind11
                             INTERFACE "${PYBIND11_INCLUDE_DIR}")

  add_library(${BBMP_CONVERSIONS_TARGET_NAME} INTERFACE)
  set_target_properties(${BBMP_CONVERSIONS_TARGET_NAME}
                        PROPERTIES PUBLIC_HEADER conversions.hpp)
  target_link_libraries(${BBMP_CONVERSIONS_TARGET_NAME} INTERFACE Python::Module
                                                                  Python::NumPy)
  target_link_libraries(${BBMP_CONVERSIONS_TARGET_NAME}
                        INTERFACE extern_pybind11)

  set(Python_EXECUTABLE
      ${Python_EXECUTABLE}
      PARENT_SCOPE)
endfunction()

function(BBMP_ADD_PYTHON_MODULE INTEROP_LIBRARY_TARGET)
  cmake_parse_arguments(
    ADD_PYTHON_MODULE_ARGS
    "" # list of names of the boolean arguments
    "" # list of names of mono-valued arguments
    "LINK_LIBRARIES" # list of names of multi-valued arguments
    ${ARGN})

  setup_variables()

  set(INTEROP_CPP
      "${CMAKE_CURRENT_BINARY_DIR}/${INTEROP_LIBRARY_TARGET}_interop.cpp")
  set(BINDING_GENERATOR_SCRIPT_PATH
      "${BBMP_INTEROP_TOOLS_PATH}/generate_cpp_to_py_bindings.py")

  create_bbmp_python_conversions_target()

  add_library(${INTEROP_LIBRARY_TARGET} SHARED ${INTEROP_CPP})
  if(UNIX)
    set_target_properties(${INTEROP_LIBRARY_TARGET} PROPERTIES PREFIX "")
  elseif(WIN32)
    set_target_properties(${INTEROP_LIBRARY_TARGET} PROPERTIES SUFFIX ".pyd")
  endif()
  target_link_libraries(${INTEROP_LIBRARY_TARGET}
                        PRIVATE ${BBMP_TYPES_TARGET_NAME})
  target_link_libraries(${INTEROP_LIBRARY_TARGET}
                        PRIVATE ${BBMP_CONVERSIONS_TARGET_NAME})

  set(SOURCES_TO_INSPECT "")
  foreach(LIB ${ADD_PYTHON_MODULE_ARGS_LINK_LIBRARIES})
    target_link_libraries(${INTEROP_LIBRARY_TARGET} PRIVATE ${LIB})
    get_target_property(LIB_SOURCES ${LIB} SOURCES)
    foreach(SOURCE_FILE ${LIB_SOURCES})
      get_filename_component(SOURCE_FILE_REALPATH ${SOURCE_FILE} REALPATH)
      list(APPEND SOURCES_TO_INSPECT \"${SOURCE_FILE_REALPATH}\")
    endforeach()
  endforeach()

  get_filename_component(INTEROP_CPP_REALPATH "${INTEROP_CPP}" REALPATH)

  add_custom_command(
    OUTPUT "${INTEROP_CPP}"
    COMMAND
      "${Python_EXECUTABLE}" "${BINDING_GENERATOR_SCRIPT_PATH}" --output
      "${INTEROP_CPP_REALPATH}" --sources "${SOURCES_TO_INSPECT}" --module_name
      "${INTEROP_LIBRARY_TARGET}"
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    DEPENDS ${ADD_PYTHON_MODULE_ARGS_LINK_LIBRARIES})
endfunction()
