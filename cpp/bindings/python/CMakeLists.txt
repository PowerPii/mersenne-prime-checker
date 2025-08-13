cmake_minimum_required(VERSION 3.20)
project(llcore_py LANGUAGES CXX)

# Ask pybind11 to locate Python the modern way and silence CMP0148
set(PYBIND11_FINDPYTHON ON)

find_package(pybind11 CONFIG REQUIRED)   # provided by Homebrew

pybind11_add_module(llcore MODULE module.cpp)
target_link_libraries(llcore PRIVATE ll_core)

# Be explicit: pull in pybind11 headers include dirs for this target
target_link_libraries(llcore PRIVATE pybind11::headers)

# (Optional) optimise Release builds of the extension too
set_property(TARGET llcore PROPERTY INTERPROCEDURAL_OPTIMIZATION $<$<CONFIG:Release>:TRUE>)
target_compile_features(llcore PRIVATE cxx_std_17)
