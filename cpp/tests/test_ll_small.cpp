#include "ll/ll.hpp"
#include <catch2/catch_test_macros.hpp>
#include <stdexcept>

TEST_CASE("Truth table: known primes/composites for M_p") {
  using ll::LLConfig; using ll::ll_test;

  // Prime exponents where M_p is prime
  for (auto p : {2u,3u,5u,7u,13u,17u,19u,31u}) {
    auto res = ll_test(LLConfig{p, false});
    REQUIRE(res.p == p);
    REQUIRE(res.iterations == (p >= 2 ? p - 2 : 0));
    REQUIRE(res.is_prime);                 // M_p should be prime
    REQUIRE(res.final_residue_is_zero);    // LL residue ends at zero
  }

  // Prime exponents where M_p is composite
  for (auto p : {11u,23u}) {
    auto res = ll_test(LLConfig{p, false});
    REQUIRE_FALSE(res.is_prime);
    REQUIRE_FALSE(res.final_residue_is_zero);
  }
}

TEST_CASE("Reject non-prime exponents") {
  using ll::LLConfig; using ll::ll_test;
  for (auto p : {0u,1u,4u,6u,8u,9u,21u}) {
    REQUIRE_THROWS_AS(ll_test(LLConfig{p, false}), std::invalid_argument);
  }
}

TEST_CASE("p == 2 fast path") {
  using ll::LLConfig; using ll::ll_test;
  auto res = ll_test(LLConfig{2u, false});
  REQUIRE(res.is_prime);
  REQUIRE(res.iterations == 0);
}
