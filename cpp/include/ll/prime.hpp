// include/ll/prime.hpp
#pragma once
#include <cstdint>

namespace ll {

// Deterministic primality for exponent p (32-bit). Returns true iff p is prime.
// Handle p=2 as prime; reject p<2; implementation will use Miller–Rabin
// with a fixed small base set valid for 32/64-bit integers.
bool is_prime_exponent(std::uint32_t p) noexcept;

} // namespace ll
