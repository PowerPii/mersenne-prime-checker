# cpp/cmake/FindGMP.cmake
# Creates imported targets: GMP::gmp (required) and GMP::gmpxx (optional)

# Common install prefixes (Apple Silicon Homebrew, Intel Homebrew, Linux)
set(_GMP_HINTS
  $ENV{GMP_ROOT}
  /opt/homebrew            # macOS arm64 (Apple Silicon)
  /usr/local               # macOS Intel / some Linux
  /usr                     # Linux
)

# Headers
find_path(GMP_INCLUDE_DIR
  NAMES gmp.h
  HINTS ${_GMP_HINTS}
  PATH_SUFFIXES include
)

# Libraries
find_library(GMP_LIBRARY
  NAMES gmp
  HINTS ${_GMP_HINTS}
  PATH_SUFFIXES lib lib64
)

# Optional C++ wrapper (only needed if you use <gmpxx.h>)
find_library(GMPXX_LIBRARY
  NAMES gmpxx
  HINTS ${_GMP_HINTS}
  PATH_SUFFIXES lib lib64
)

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(GMP
  REQUIRED_VARS GMP_INCLUDE_DIR GMP_LIBRARY
)

if(GMP_FOUND)
  if(NOT TARGET GMP::gmp)
    add_library(GMP::gmp UNKNOWN IMPORTED)
    set_target_properties(GMP::gmp PROPERTIES
      IMPORTED_LOCATION             "${GMP_LIBRARY}"
      INTERFACE_INCLUDE_DIRECTORIES "${GMP_INCLUDE_DIR}"
    )
  endif()

  # Optional C++ wrapper target
  if(GMPXX_LIBRARY AND NOT TARGET GMP::gmpxx)
    add_library(GMP::gmpxx UNKNOWN IMPORTED)
    set_target_properties(GMP::gmpxx PROPERTIES
      IMPORTED_LOCATION             "${GMPXX_LIBRARY}"
      INTERFACE_LINK_LIBRARIES      GMP::gmp
      INTERFACE_INCLUDE_DIRECTORIES "${GMP_INCLUDE_DIR}"
    )
  endif()
endif()

mark_as_advanced(GMP_INCLUDE_DIR GMP_LIBRARY GMPXX_LIBRARY)
