// src/mersenne_reduce.cpp
#include <cstdint>
#include <gmp.h>

namespace ll {
void mersenne_reduce_once(mpz_t x, const mpz_t M, std::uint32_t p, mpz_t hi) {
  mpz_tdiv_q_2exp(hi, x, p); // hi = x >> p
  mpz_tdiv_r_2exp(x, x, p);  // x  = x & ((1<<p)-1)
  mpz_add(x, x, hi);         // x += hi
  if (mpz_cmp(x, M) >= 0) {
    mpz_sub(x, x, M);
  }
  if (mpz_cmp(x, M) >= 0) {
    mpz_sub(x, x, M);
  } // rare x==2M case
}
} // namespace ll
