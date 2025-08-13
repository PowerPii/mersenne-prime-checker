// include/ll/ll.hpp
#pragma once
#include <cstdint>
#include <array>
#include <functional>
#include <string>

namespace ll {

// Bump when the wire contract changes (handy for logging/UI).
inline constexpr const char* LL_VERSION = "0.1.0";

// Opaque, fixed-size digest of the current residue (stable across runs).
struct ResidueDigest {
  std::array<std::uint8_t, 32> bytes{}; // 256-bit
};

// Optional knobs; keep minimal now for a clean API.
struct LLConfig {
  std::uint32_t p;                    // exponent (assumed <= 2^32-1)
  bool enable_progress = true;        // allow callbacks
  std::uint32_t progress_stride = 0;  // 0 = auto (~1% of total)
};

// Result summary; no internal types leaked.
struct LLResult {
  std::uint32_t p = 0;
  bool is_prime = false;
  std::uint64_t iterations = 0;       // should equal (p >= 2 ? p - 2 : 0)
  std::uint64_t ns_elapsed = 0;       // wall-clock nanoseconds (best effort)
  bool final_residue_is_zero = false; // sanity flag for LL correctness
  std::string  engine_info;           // e.g., "gmp:6.3.0; fft:toom/fft; cpu:apple-m1"
};

// Progress callback: iteration index (0..p-3) and a residue digest.
using ProgressCb = std::function<void(std::uint32_t, const ResidueDigest&)>;

// Single entrypoint: runs the Lucas–Lehmer test for M_p = 2^p - 1.
// Throws std::invalid_argument if p < 2 or p is not prime (exponent must be prime).
LLResult ll_test(const LLConfig& cfg, ProgressCb cb = {});

} // namespace ll
