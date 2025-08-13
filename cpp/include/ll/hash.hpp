// include/ll/hash.hpp
#pragma once
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>
#include "ll.hpp"  // for ll::ResidueDigest

namespace ll {

// Compute a stable 256-bit digest over arbitrary bytes (used to hash the residue limbs).
// Implementation can use SHA-256 (or any stable algorithm); callers don't depend on details.
ResidueDigest make_residue_digest(const void* data, std::size_t nbytes) noexcept;

// Convenience overloads for tests/logging.
ResidueDigest make_residue_digest(const std::string& s) noexcept;
ResidueDigest make_residue_digest(const std::vector<std::uint8_t>& v) noexcept;

// Hex encoding for logs and debugging.
std::string to_hex(const ResidueDigest& d);

} // namespace ll
