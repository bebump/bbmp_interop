/*
 * Copyright (c) 2020 Attila Szarvas <attila.szarvas@gmail.com>
 *
 * All rights reserved. Use of this source code is governed the 3-Clause BSD
 * License BSD-style license that can be found in the LICENSE file.
 */

/*
 * This header may be included by the generated Python extension module to
 * convert numpy `ndarray` arguments (`pybind11::array_t<T, 0>`) to
 * `OwnedChannelData<T>`.
 *
 * There shouldn't be any reason to dependencies this file in targets that aren't
 * Python extension modules themselves.
 *
 * In the Python module `OwnedChannelData<T>` parameters will be replaced by
 * numpy `ndarray`s. The conversion between the two is the purpose of this file.
 */

#pragma once

#include "types.hpp"

#include "pybind11/numpy.h"
#include "pybind11/pybind11.h"

template <typename T>
using NumpyNdarray = pybind11::array_t<T, 0>;

template <typename T>
inline void assert_c_contiguous(const NumpyNdarray<T>& arr) {
  const int NUMPY_ARRAY_C_CONTIGUOUS = 0x0001;

  if ((arr.flags() & NUMPY_ARRAY_C_CONTIGUOUS) == 0) {
    throw std::domain_error("ndarray argument is not C contiguous");
  }
}

namespace bbmp {
template <typename T>
OwnedChannelData<T> createOwnedChannelData(NumpyNdarray<T>&& ndarray) {
  assert_c_contiguous(ndarray);

  if (ndarray.ndim() > 2) {
    throw std::domain_error("At most two-dimensional arrays are supported.");
  }

  auto typed_heap_object = moveOntoHeap(std::move(ndarray));
  auto raw_ptr = typed_heap_object.get();
  auto heap_object = makeTypeErasedUniquePtr(std::move(typed_heap_object));

  int num_channels = 0;
  size_t length = 0;
  if (raw_ptr->ndim() == 1) {
    num_channels = 1;
    length = raw_ptr->shape(0);
  } else if (raw_ptr->ndim() == 2) {
    num_channels = bbmp::asserted_static_cast_int(raw_ptr->shape(0));
    length = raw_ptr->shape(1);
  }

  auto get_ch_ptr = [raw_ptr, length](const int num_ch) noexcept {
    return raw_ptr->mutable_unchecked().mutable_data() + num_ch * length;
  };
  return {std::move(heap_object), num_channels, length, std::move(get_ch_ptr)};
}
}  // namespace bbmp
