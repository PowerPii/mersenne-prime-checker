#include "ll/ll.hpp"
#include "ll/hash.hpp"
#include <iostream>
#include <vector>
#include <string>
#include <limits>
#include <chrono>

int main(int argc, char** argv) {
  // Flags: --bench=N (repeat), --stride=K, --no-progress
  unsigned repeats = 1, stride = 0;   // 0 = auto (~1%)
  bool enable_progress = true;
  std::vector<std::uint32_t> exps;

  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    if (a.rfind("--bench=", 0) == 0) {
      repeats = std::stoul(a.substr(8));
    } else if (a.rfind("--stride=", 0) == 0) {
      stride = std::stoul(a.substr(9));
    } else if (a == "--no-progress") {
      enable_progress = false;
    } else {
      unsigned long long v = 0;
      try { v = std::stoull(a); } catch (...) { std::cerr << "skip '"<<a<<"'\n"; continue; }
      if (v > std::numeric_limits<std::uint32_t>::max()) {
        std::cerr << "skip '"<<a<<"': out of 32-bit range\n"; continue;
      }
      exps.push_back(static_cast<std::uint32_t>(v));
    }
  }
  if (exps.empty()) exps = {31};

  for (auto p : exps) {
    auto progress = [&](std::uint32_t iter, const ll::ResidueDigest& d) {
      (void)d;
      static int last = -1;
      const unsigned total = (p >= 2 ? p - 2 : 0);
      if (!total) return;
      int pct = int((iter + 1) * 100 / total);
      if (pct / 20 > last) {  // print at ~20% steps
        std::cout << "  p="<<p<<" "<<pct<<"%\n";
        last = pct / 20;
      }
    };

    std::uint64_t best = UINT64_MAX, sum = 0;
    for (unsigned r = 0; r < repeats; ++r) {
      ll::LLConfig cfg{p, enable_progress, stride};
      auto t0 = std::chrono::steady_clock::now();
      auto res = ll::ll_test(cfg, enable_progress ? progress : ll::ProgressCb{});
      auto t1 = std::chrono::steady_clock::now();
      auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(t1 - t0).count();
      sum += ns; if ((std::uint64_t)ns < best) best = ns;
      if (repeats == 1) {
        std::cout << "M_"<<p<<" → "<<(res.is_prime?"PRIME":"COMPOSITE")
                  <<" | iters="<<res.iterations<<" | core(ns)="<<ns
                  <<" | engine="<<res.engine_info<<"\n";
      }
    }
    if (repeats > 1) {
      std::cout << "M_"<<p<<" bench repeats="<<repeats
                <<" | best(ns)="<<best<<" | avg(ns)="<< (sum / repeats) << "\n";
    }
  }
  return 0;
}
