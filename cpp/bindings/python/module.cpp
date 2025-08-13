#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/pytypes.h>
#include <pybind11/stl.h>
#include <cstdint>
#include <optional>
#include <string>       
#include <stdexcept>    
#include <gmp.h>
#include <cstdio>

#include "ll/ll.hpp"

namespace py = pybind11;

static py::bytes digest_to_bytes(const ll::ResidueDigest& d) {
  return py::bytes(reinterpret_cast<const char*>(d.bytes.data()), d.bytes.size());
}

static py::dict ll_test_py(std::uint32_t p,
                           std::uint32_t progress_stride = 0,
                           std::optional<py::function> callback = std::nullopt) {

  ll::LLConfig cfg{p, /*enable_progress=*/callback.has_value(), progress_stride};

  // Prepare C++ progress callback that reacquires the GIL when invoked.
  ll::ProgressCb cb_cpp;
  if (callback.has_value()) {
    py::function fn = *callback;
    cb_cpp = [fn = std::move(fn)](std::uint32_t iter, const ll::ResidueDigest& d) {
      py::gil_scoped_acquire gil;
      fn(iter, digest_to_bytes(d));
    };
  }

  // Release the GIL for the heavy computation.
  ll::LLResult res;
  {
    py::gil_scoped_release nogil;
    res = ll::ll_test(cfg, cb_cpp);
  }

  // Return a small, JSON-friendly dict
  py::dict out;
  out["p"] = res.p;
  out["is_prime"] = res.is_prime;
  out["iterations"] = py::int_(res.iterations);
  out["ns_elapsed"] = py::int_(res.ns_elapsed);
  out["final_residue_is_zero"] = res.final_residue_is_zero;
  out["engine_info"] = res.engine_info;
  return out;
}

static py::dict write_mersenne_decimal_py(std::uint32_t p, const std::string& path) {
  if (p < 1) throw std::invalid_argument("p must be >= 1");

  mpz_t M; mpz_init2(M, p + 1);
  mpz_set_ui(M, 1); mpz_mul_2exp(M, M, p); mpz_sub_ui(M, M, 1);

  std::FILE* f = std::fopen(path.c_str(), "wb");
  if (!f) { mpz_clear(M); throw std::runtime_error("cannot open output file"); }

  size_t written = mpz_out_str(f, 10, M);   // exact digits written
  std::fputc('\n', f);
  std::fclose(f);
  mpz_clear(M);
  if (written == 0) throw std::runtime_error("mpz_out_str failed");

  py::dict out;
  out["p"] = p;
  out["path"] = path;
  out["digits"] = py::int_(written);        // use written (exact)
  out["written_digits"] = py::int_(written);
  return out;
}

PYBIND11_MODULE(llcore, m) {
  m.doc() = "Lucas-Lehmer core (pybind11)";

  m.def("ll_test", &ll_test_py,
      py::arg("p"),
      py::arg("progress_stride") = 0,         // 0 => auto (~1% of p-2)
      py::arg("callback") = py::none(),
      R"pbdoc(
Run the Lucas–Lehmer test for M_p = 2^p - 1.

Args:
  p (int): prime exponent p >= 2.
  progress_stride (int): 0 for auto (~1% of (p−2)); otherwise invoke the callback every N iterations.
  callback (callable): optional function (iter:int, digest:bytes) -> None.

Returns:
  dict { p, is_prime, iterations, ns_elapsed, final_residue_is_zero, engine_info }.
)pbdoc");

  m.def("write_mersenne_decimal", &write_mersenne_decimal_py,
        py::arg("p"), py::arg("path"),
        R"pbdoc(Write M_p = 2^p - 1 to `path` in base-10; returns metadata.)pbdoc");
}
