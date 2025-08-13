// src/ll_core.cpp
#include "ll/hash.hpp"
#include "ll/ll.hpp"
#include "ll/prime.hpp"

#include <algorithm> // std::max
#include <chrono>
#include <cstdint>
#include <gmp.h>
#include <stdexcept>
#include <string>

namespace {
inline std::string compiler_info() {
#if defined(__clang__)
  return std::string("clang:") + __clang_version__;
#elif defined(__GNUC__)
  return std::string("gcc:") + __VERSION__;
#else
  return "cxx:?";
#endif
}
} // namespace

namespace ll {
// Forward decl for the internal reducer (no public header exposure)
void mersenne_reduce_once(mpz_t x, const mpz_t M, std::uint32_t p, mpz_t hi);
} // namespace ll

namespace ll {

LLResult ll_test(const LLConfig &cfg, ProgressCb cb) {
  const std::uint32_t p = cfg.p;
  if (p < 2)
    throw std::invalid_argument("p must be >= 2");
  if (!is_prime_exponent(p))
    throw std::invalid_argument("exponent p must be prime");

  // Fast path: p == 2  => M_2 = 3 is prime; LL has zero iterations.
  if (p == 2) {
    LLResult quick;
    quick.p = 2;
    quick.iterations = 0;
    quick.ns_elapsed = 0;
    quick.final_residue_is_zero = true; // by convention; LL loop not run
    quick.is_prime = true;
    quick.engine_info = std::string("gmp:") +
                        (::gmp_version ? ::gmp_version : "?") + "; " +
                        compiler_info() + "; flags:native";
    return quick;
  }

  LLResult out;
  out.p = p;
  out.iterations = static_cast<std::uint64_t>(p - 2);

  // Compute effective progress stride (0 => auto ~1%).
  const std::uint32_t total_iters = p - 2;
  const std::uint32_t stride = (cfg.progress_stride != 0)
                                   ? cfg.progress_stride
                                   : std::max(1u, total_iters / 100);

  auto t0 = std::chrono::steady_clock::now();

  // Big integers: preallocate to avoid reallocations
  mpz_t M, s, tmp, hi;
  mpz_init2(M, p + 1);       // M ~ p bits
  mpz_init2(s, p + 1);       // residue s < 2^p
  mpz_init2(tmp, 2 * p + 2); // s^2 - 2 < 2^(2p)
  mpz_init2(hi, p + 1);

  // M = 2^p - 1
  mpz_set_ui(M, 1);
  mpz_mul_2exp(M, M, p);
  mpz_sub_ui(M, M, 1);

  // s = 4
  mpz_set_ui(s, 4);

  bool early_composite = false;

  // Lucas–Lehmer loop: exactly p-2 iterations
  for (std::uint32_t i = 0; i < total_iters; ++i) {
    // Early exit: if previous iteration produced s==0 and we still have work,
    // M_p is composite.
    if (i > 0 && mpz_cmp_ui(s, 0) == 0) {
      out.final_residue_is_zero = false;
      out.is_prime = false;
      early_composite = true;
      break;
    }

    // tmp = s*s - 2
    mpz_mul(tmp, s, s);
    mpz_sub_ui(tmp, tmp, 2);

    // One-fold Mersenne reduction into [0, M-1]
    mersenne_reduce_once(tmp, M, p, hi);

    // s <- tmp
    mpz_swap(s, tmp);

#if defined(LL_ENABLE_DEBUG_INVARIANTS) || !defined(NDEBUG)
    if (mpz_sgn(s) < 0 || mpz_cmp(s, M) >= 0)
      throw std::logic_error("LL invariant violated: residue out of range");
#endif

    // Throttled, zero-copy progress hashing
    if (cb && cfg.enable_progress &&
        ((i + 1) % stride == 0 || i + 1 == total_iters)) {
      size_t nlimbs = mpz_size(s);
      const mp_limb_t *limbs = mpz_limbs_read(s);
      cb(i, make_residue_digest(limbs, nlimbs * sizeof(mp_limb_t)));
    }
  }

  if (!early_composite) {
    out.final_residue_is_zero = (mpz_cmp_ui(s, 0) == 0);
    out.is_prime = out.final_residue_is_zero;
  }

  // Cleanup
  mpz_clear(M);
  mpz_clear(s);
  mpz_clear(tmp);
  mpz_clear(hi);

  auto t1 = std::chrono::steady_clock::now();
  out.ns_elapsed = static_cast<std::uint64_t>(
      std::chrono::duration_cast<std::chrono::nanoseconds>(t1 - t0).count());

  // Engine info
  out.engine_info = std::string("gmp:") +
                    (::gmp_version ? ::gmp_version : "?") + "; " +
                    compiler_info() + "; flags:native";

  return out;
}

} // namespace ll
