cmake_minimum_required(VERSION 3.20)
include(FetchContent)

FetchContent_Declare(
  catch2
  GIT_REPOSITORY https://github.com/catchorg/Catch2.git
  GIT_TAG v3.5.3
)
FetchContent_MakeAvailable(catch2)

add_executable(ll_tests
  test_ll_small.cpp
  test_progress.cpp
)

target_link_libraries(ll_tests PRIVATE
  ll_core
  Catch2::Catch2WithMain
)

add_test(NAME ll_tests COMMAND ll_tests)
