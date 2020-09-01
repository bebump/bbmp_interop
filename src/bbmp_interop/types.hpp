/*
 * Copyright (c) 2020 Attila Szarvas <attila.szarvas@gmail.com>
 *
 * All rights reserved. Use of this source code is governed the 3-Clause BSD
 * License BSD-style license that can be found in the LICENSE file.
 */

#pragma once

#include <array>
#include <cassert>
#include <functional>
#include <limits>
#include <memory>
#include <type_traits>
#include <vector>

namespace bbmp {

inline int asserted_static_cast_int(size_t value) {
  assert(value <= std::numeric_limits<int>::max());
  return static_cast<int>(value);
}

using TypeErasedUniquePtr = std::unique_ptr<void, void (*)(void*)>;

template <typename T>
TypeErasedUniquePtr makeTypeErasedUniquePtr(T* obj) {
  return TypeErasedUniquePtr(obj, [](void* p) { delete static_cast<T*>(p); });
}

template <typename T>
TypeErasedUniquePtr makeTypeErasedUniquePtr(std::unique_ptr<T> obj) {
  return TypeErasedUniquePtr(obj.release(),
                             [](void* p) { delete static_cast<T*>(p); });
}

template <typename T>
std::unique_ptr<T> moveOntoHeap(T&& obj) {
  return std::make_unique<T>(std::move(obj));
}

template <typename T>
class OwnedChannelData {
 public:
  OwnedChannelData(TypeErasedUniquePtr&& owning_ptr, const int num_channels,
                   const size_t length,
                   const std::function<T*(int)>& ch_ptr_getter)
      : num_channels_(num_channels),
        length_(length),
        heap_object_(std::move(owning_ptr)) {
    ptrs_ = decltype(ptrs_)(new T*[num_channels]);
    for (auto i = 0; i < num_channels; ++i) {
      ptrs_[i] = ch_ptr_getter(i);
    }
  }

  T* GetWriteChannelPtr(const int channel_ix) noexcept {
    return ptrs_[channel_ix];
  }

  const T* GetReadChannelPtr(const int channel_ix) const noexcept {
    return ptrs_[channel_ix];
  }

  T** GetWritePtrs() noexcept {
    return ptrs_.get();
  }

  T const * const * GetReadPtrs() const noexcept {
    return ptrs_.get();
  }

  operator bool() noexcept { return heap_object_.operator bool(); }

  size_t length() const noexcept { return length_; }

  int num_channels() const noexcept { return num_channels_; }

 private:
  int num_channels_;
  size_t length_;
  TypeErasedUniquePtr heap_object_;
  std::unique_ptr<T*[]> ptrs_;
};

template <typename T>
OwnedChannelData<T> createOwnedChannelData(
    std::vector<std::vector<T>>&& channelsData) {
  assert(channelsData.size() > 0);
  using object_type = typename std::remove_reference<decltype(channelsData)>::type;
  auto raw_ptr = new object_type{std::move(channelsData)};
  auto heap_object = makeTypeErasedUniquePtr(raw_ptr);
  auto get_ch_ptr = [raw_ptr](const int num_ch) noexcept {
    return raw_ptr->at(num_ch).data();
  };
  return OwnedChannelData<T>(std::move(heap_object),
                             asserted_static_cast_int(raw_ptr->size()),
                             raw_ptr->at(0).size(), std::move(get_ch_ptr));
}

template <typename T>
class ChannelsData {
 public:
  ChannelsData(T** ptrs, const int num_channels, const int length)
      : ptrs_(ptrs),
        num_channels_(num_channels),
        length_(length),
        num_slices_(0) {}

  ChannelsData<T> subView(const int start_ix, const int length) {}

 private:
  T** ptrs_;
  int num_channels_;
  int length_;
  std::array<int, 6> slices_;
  int num_slices_;
};
}  // namespace bbmp
