#include "ll/ll.hpp"
#include <catch2/catch_test_macros.hpp>
#include <atomic>

TEST_CASE("Progress callback fires once per iteration") {
  using ll::LLConfig; using ll::ResidueDigest; using ll::ll_test;

  std::atomic<unsigned> hits{0};
  auto cb = [&](std::uint32_t /*iter*/, const ResidueDigest& /*d*/) { ++hits; };

  const unsigned p = 7; // p-2 = 5 steps
  auto res = ll_test(LLConfig{p, true}, cb);
  REQUIRE(res.p == p);
  REQUIRE(hits.load() == p - 2);
}
