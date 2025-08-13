// src/prime.cpp
#include "ll/prime.hpp"
#include <cstdint>

namespace ll {
static inline std::uint64_t mod_mul(std::uint64_t a, std::uint64_t b,
                                    std::uint64_t m) {
  return static_cast<std::uint64_t>((__uint128_t)a * b %
                                    m); // safe for 64-bit intermediates
}

static inline std::uint64_t mod_pow(std::uint64_t a, std::uint64_t e,
                                    std::uint64_t m) {
  std::uint64_t r = 1 % m;
  while (e) {
    if (e & 1)
      r = mod_mul(r, a, m);
    a = mod_mul(a, a, m);
    e >>= 1;
  }
  return r;
}

static bool mr_witness(std::uint32_t n, std::uint32_t a) {
  if (a % n == 0)
    return true; // base equals 0 mod n → “passes” this base
  std::uint32_t d = n - 1;
  unsigned s = 0;
  while ((d & 1u) == 0) {
    d >>= 1;
    ++s;
  } // n-1 = d * 2^s with d odd
  std::uint64_t x = mod_pow(a, d, n);
  if (x == 1 || x == n - 1)
    return true;
  for (unsigned i = 1; i < s; ++i) {
    x = mod_mul(x, x, n);
    if (x == n - 1)
      return true;
  }
  return false; // composite for this base
}

bool is_prime_exponent(std::uint32_t p) noexcept {
  if (p == 2)
    return true;
  if (p < 2 || (p & 1u) == 0)
    return false;

  // quick small-prime trial division (fast path and handles exact small primes)
  static constexpr std::uint32_t small[] = {3u,  5u,  7u,  11u, 13u, 17u,
                                            19u, 23u, 29u, 31u, 37u};
  for (std::uint32_t q : small) {
    if (p == q)
      return true;
    if (p % q == 0)
      return false;
  }

  // Deterministic for 32-bit integers with these bases.
  static constexpr std::uint32_t bases[] = {2u, 3u, 5u, 7u, 11u};
  for (std::uint32_t a : bases) {
    if (!mr_witness(p, a))
      return false;
  }
  return true;
}

} // namespace ll
