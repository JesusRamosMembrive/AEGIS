cmake_minimum_required(VERSION 3.20)
project(static_analysis_motor
    VERSION 0.1.0
    DESCRIPTION "AEGIS C++ Static Analysis Motor"
    LANGUAGES CXX
)

# ==============================================================================
# C++ Standard Configuration
# ==============================================================================
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Export compile_commands.json for IDE integration
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ==============================================================================
# Compiler Warnings (Strict for quality)
# ==============================================================================
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(
        -Wall
        -Wextra
        -Wpedantic
        -Werror
        -Wno-unused-parameter
        -Wshadow
        -Wconversion
        -Wsign-conversion
    )
elseif(MSVC)
    add_compile_options(/W4 /WX /permissive-)
endif()

# ==============================================================================
# Dependencies via FetchContent
# ==============================================================================
include(FetchContent)

# nlohmann/json - Header-only JSON library
FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(json)

# Google Test - Testing framework (only for tests)
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.14.0
    GIT_SHALLOW TRUE
)
# Prevent overriding parent project's compiler/linker settings on Windows
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

# ==============================================================================
# Find libclang
# ==============================================================================
find_package(Clang QUIET)
if(NOT Clang_FOUND)
    # Fallback: try to find libclang directly
    find_library(LIBCLANG_LIBRARY NAMES clang libclang
        PATHS
            /usr/lib/llvm-18/lib
            /usr/lib/llvm-17/lib
            /usr/lib/llvm-16/lib
            /usr/lib/llvm-15/lib
            /usr/lib/llvm-14/lib
            /usr/lib/x86_64-linux-gnu
            /usr/local/lib
            /opt/homebrew/lib
    )
    find_path(LIBCLANG_INCLUDE_DIR clang-c/Index.h
        PATHS
            /usr/lib/llvm-18/include
            /usr/lib/llvm-17/include
            /usr/lib/llvm-16/include
            /usr/lib/llvm-15/include
            /usr/lib/llvm-14/include
            /usr/include
            /usr/local/include
            /opt/homebrew/include
    )
    if(LIBCLANG_LIBRARY AND LIBCLANG_INCLUDE_DIR)
        message(STATUS "Found libclang: ${LIBCLANG_LIBRARY}")
        message(STATUS "Found libclang headers: ${LIBCLANG_INCLUDE_DIR}")
    else()
        message(WARNING "libclang not found. Analyzer features will be disabled.")
        set(LIBCLANG_LIBRARY "")
        set(LIBCLANG_INCLUDE_DIR "")
    endif()
else()
    message(STATUS "Found Clang package")
    set(LIBCLANG_LIBRARY libclang)
    get_target_property(LIBCLANG_INCLUDE_DIR libclang INTERFACE_INCLUDE_DIRECTORIES)
endif()

# ==============================================================================
# Main Library: libaegis-cpp
# ==============================================================================
add_library(aegis_cpp_lib STATIC
    src/scanner.cpp
    src/metrics.cpp
    src/analyzer.cpp
    src/ipc/socket_server.cpp
    src/ipc/json_protocol.cpp
)

target_include_directories(aegis_cpp_lib
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/src
    PRIVATE
        ${LIBCLANG_INCLUDE_DIR}
)

target_link_libraries(aegis_cpp_lib
    PUBLIC
        nlohmann_json::nlohmann_json
    PRIVATE
        ${LIBCLANG_LIBRARY}
)

# Platform-specific socket libraries
if(WIN32)
    target_link_libraries(aegis_cpp_lib PRIVATE ws2_32)
endif()

# ==============================================================================
# Main Executable: static-analysis-motor
# ==============================================================================
add_executable(static_analysis_motor src/main.cpp)

target_link_libraries(static_analysis_motor PRIVATE aegis_cpp_lib)

# ==============================================================================
# Tests
# ==============================================================================
enable_testing()
add_subdirectory(tests)

# ==============================================================================
# Installation
# ==============================================================================
install(TARGETS static_analysis_motor
    RUNTIME DESTINATION bin
)
