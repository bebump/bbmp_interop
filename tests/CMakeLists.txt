# Copyright (c) 2020 Attila Szarvas <attila.szarvas@gmail.com>
#
# All rights reserved. Use of this source code is governed the 3-Clause BSD
# License BSD-style license that can be found in the LICENSE file.

cmake_minimum_required(VERSION 3.12)

project(bbmp-interop-test)
add_library(bbmp_interop_test STATIC test.cpp)
target_link_libraries(bbmp_interop_test PRIVATE bbmp_types)
bbmp_add_python_module(pybbmp_interop_test LINK_LIBRARIES bbmp_interop_test)
