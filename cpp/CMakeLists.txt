cmake_minimum_required(VERSION 3.20)
project(mersenne LANGUAGES C CXX)

# Basics
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Find GMP via our local FindGMP.cmake
list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")
find_package(GMP REQUIRED)

# ---- Core library -----------------------------------------------------------
add_library(ll_core STATIC
  src/ll_core.cpp
  src/mersenne_reduce.cpp
  src/prime.cpp
  src/hash.cpp
)
target_include_directories(ll_core PUBLIC include)
target_link_libraries(ll_core PRIVATE GMP::gmp)

# Optimise Release builds
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION_RELEASE ON)  # global LTO for Release
target_compile_options(ll_core PRIVATE $<$<CONFIG:Release>:-O3 -march=native>)
target_compile_definitions(ll_core PRIVATE $<$<CONFIG:Release>:NDEBUG>)
set_property(TARGET ll_core PROPERTY INTERPROCEDURAL_OPTIMIZATION $<$<CONFIG:Release>:TRUE>)

# ---- CLI -------------------------------------------------------------------
add_executable(ll_cli cli/ll_cli.cpp)
target_link_libraries(ll_cli PRIVATE ll_core)
set_property(TARGET ll_cli PROPERTY INTERPROCEDURAL_OPTIMIZATION $<$<CONFIG:Release>:TRUE>)

# ---- Tests -----------------------------------------------------------------
include(CTest)
if (BUILD_TESTING)
  enable_testing()
  add_subdirectory(tests)
endif()

# ---- Python bindings (pybind11) --------------------------------------------
# Use the subdirectory (which can either FetchContent or find_package pybind11).
option(BUILD_PY "Build Python bindings (llcore module)" ON)
if (BUILD_PY)
  add_subdirectory(bindings/python)
endif()
