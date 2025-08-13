// src/hash.cpp
#include "ll/hash.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

namespace ll {
namespace {

// ---- Minimal SHA-256 (one-shot) ----
inline constexpr std::uint32_t rotr(std::uint32_t x, int n) {
  return (x >> n) | (x << (32 - n));
}
inline std::uint32_t load_be32(const unsigned char *p) {
  return (std::uint32_t)p[0] << 24 | (std::uint32_t)p[1] << 16 |
         (std::uint32_t)p[2] << 8 | (std::uint32_t)p[3];
}
inline void store_be32(unsigned char *p, std::uint32_t v) {
  p[0] = (unsigned char)(v >> 24);
  p[1] = (unsigned char)(v >> 16);
  p[2] = (unsigned char)(v >> 8);
  p[3] = (unsigned char)(v);
}

static void sha256(const void *data, std::size_t len,
                   std::array<std::uint8_t, 32> &out) {
  static constexpr std::uint32_t K[64] = {
      0x428a2f98u, 0x71374491u, 0xb5c0fbcfu, 0xe9b5dba5u, 0x3956c25bu,
      0x59f111f1u, 0x923f82a4u, 0xab1c5ed5u, 0xd807aa98u, 0x12835b01u,
      0x243185beu, 0x550c7dc3u, 0x72be5d74u, 0x80deb1feu, 0x9bdc06a7u,
      0xc19bf174u, 0xe49b69c1u, 0xefbe4786u, 0x0fc19dc6u, 0x240ca1ccu,
      0x2de92c6fu, 0x4a7484aau, 0x5cb0a9dcu, 0x76f988dau, 0x983e5152u,
      0xa831c66du, 0xb00327c8u, 0xbf597fc7u, 0xc6e00bf3u, 0xd5a79147u,
      0x06ca6351u, 0x14292967u, 0x27b70a85u, 0x2e1b2138u, 0x4d2c6dfcu,
      0x53380d13u, 0x650a7354u, 0x766a0abbu, 0x81c2c92eu, 0x92722c85u,
      0xa2bfe8a1u, 0xa81a664bu, 0xc24b8b70u, 0xc76c51a3u, 0xd192e819u,
      0xd6990624u, 0xf40e3585u, 0x106aa070u, 0x19a4c116u, 0x1e376c08u,
      0x2748774cu, 0x34b0bcb5u, 0x391c0cb3u, 0x4ed8aa4au, 0x5b9cca4fu,
      0x682e6ff3u, 0x748f82eeu, 0x78a5636fu, 0x84c87814u, 0x8cc70208u,
      0x90befffau, 0xa4506cebu, 0xbef9a3f7u, 0xc67178f2u};
  std::uint32_t H[8] = {0x6a09e667u, 0xbb67ae85u, 0x3c6ef372u, 0xa54ff53au,
                        0x510e527fu, 0x9b05688cu, 0x1f83d9abu, 0x5be0cd19u};

  const unsigned char *in = static_cast<const unsigned char *>(data);
  std::size_t full = len / 64 * 64;
  unsigned char block[64];

  auto compress = [&](const unsigned char *b) {
    std::uint32_t w[64];
    for (int i = 0; i < 16; ++i)
      w[i] = load_be32(b + 4 * i);
    for (int i = 16; i < 64; ++i) {
      std::uint32_t s0 =
          rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
      std::uint32_t s1 =
          rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
      w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    std::uint32_t a = H[0], b2 = H[1], c = H[2], d = H[3], e = H[4], f = H[5],
                  g = H[6], h = H[7];
    for (int i = 0; i < 64; ++i) {
      std::uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      std::uint32_t ch = (e & f) ^ (~e & g);
      std::uint32_t t1 = h + S1 + ch + K[i] + w[i];
      std::uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      std::uint32_t maj = (a & b2) ^ (a & c) ^ (b2 & c);
      std::uint32_t t2 = S0 + maj;
      h = g;
      g = f;
      f = e;
      e = d + t1;
      d = c;
      c = b2;
      b2 = a;
      a = t1 + t2;
    }
    H[0] += a;
    H[1] += b2;
    H[2] += c;
    H[3] += d;
    H[4] += e;
    H[5] += f;
    H[6] += g;
    H[7] += h;
  };

  // Process full blocks
  for (std::size_t i = 0; i < full; i += 64)
    compress(in + i);

  // Padding
  std::size_t rem = len - full;
  std::memset(block, 0, 64);
  if (rem)
    std::memcpy(block, in + full, rem);
  block[rem] = 0x80;

  if (rem >= 56) { // need two blocks
    compress(block);
    std::memset(block, 0, 64);
  }
  // length in bits (big-endian)
  std::uint64_t bits = static_cast<std::uint64_t>(len) * 8;
  for (int i = 0; i < 8; ++i)
    block[56 + 7 - i] = (unsigned char)(bits >> (8 * i));
  compress(block);

  // Output
  for (int i = 0; i < 8; ++i)
    store_be32(out.data() + 4 * i, H[i]);
}

} // namespace

ResidueDigest make_residue_digest(const void *data,
                                  std::size_t nbytes) noexcept {
  ResidueDigest d{};
  sha256(data, nbytes, d.bytes);
  return d;
}

ResidueDigest make_residue_digest(const std::string &s) noexcept {
  return make_residue_digest(s.data(), s.size());
}

ResidueDigest make_residue_digest(const std::vector<std::uint8_t> &v) noexcept {
  return make_residue_digest(v.data(), v.size());
}

std::string to_hex(const ResidueDigest &d) {
  static const char *hex = "0123456789abcdef";
  std::string out;
  out.resize(d.bytes.size() * 2);
  for (std::size_t i = 0; i < d.bytes.size(); ++i) {
    out[2 * i] = hex[(d.bytes[i] >> 4) & 0xF];
    out[2 * i + 1] = hex[d.bytes[i] & 0xF];
  }
  return out;
}

} // namespace ll
