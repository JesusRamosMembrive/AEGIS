# Tests CMakeLists.txt

include(GoogleTest)

# Test executable
add_executable(aegis_cpp_tests
    test_scanner.cpp
    test_metrics.cpp
)

target_link_libraries(aegis_cpp_tests
    PRIVATE
        aegis_cpp_lib
        GTest::gtest_main
)

# Enable test discovery
gtest_discover_tests(aegis_cpp_tests)
