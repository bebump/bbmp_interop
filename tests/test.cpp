/*
 * Copyright (c) 2020 Attila Szarvas <attila.szarvas@gmail.com>
 *
 * All rights reserved. Use of this source code is governed the 3-Clause BSD
 * License BSD-style license that can be found in the LICENSE file.
 */

#include "bbmp_interop/types.hpp"

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
std::string hello() {
  return "Hello from C++";
}

namespace test_namespace {
EXPORT_TO_PYTHON
void add_to_array(bbmp::OwnedChannelData<float>& data, const float number) {
  for (int chIx = 0; chIx < data.num_channels(); ++chIx) {
    auto ptr = data.GetWriteChannelPtr(chIx);
    for (size_t i = 0; i < data.length(); ++i) *(ptr + i) += number;
  }
}
}  // namespace test_namespace
