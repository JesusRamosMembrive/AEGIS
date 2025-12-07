#include "../src/metrics.hpp"

#include <gtest/gtest.h>
#include <filesystem>
#include <fstream>

namespace aegis::test {

class MetricsTest : public ::testing::Test {
protected:
    void SetUp() override
    {
        test_dir_ = std::filesystem::temp_directory_path() / "aegis_test_metrics";
        std::filesystem::remove_all(test_dir_);
        std::filesystem::create_directories(test_dir_);
    }

    void TearDown() override
    {
        std::filesystem::remove_all(test_dir_);
    }

    std::filesystem::path create_file(const std::string& name, const std::string& content)
    {
        auto path = test_dir_ / name;
        std::ofstream file(path);
        file << content;
        return path;
    }

    std::filesystem::path test_dir_;
};

TEST_F(MetricsTest, CalculateFileLoc_SimpleFile)
{
    auto path = create_file("simple.cpp",
        "int main() {\n"
        "    return 0;\n"
        "}\n"
    );

    auto metrics = calculate_file_loc(path);
    ASSERT_TRUE(metrics.has_value());

    EXPECT_EQ(metrics->path, path);
    EXPECT_EQ(metrics->total_lines, 3u);
    EXPECT_EQ(metrics->code_lines, 3u);
    EXPECT_EQ(metrics->blank_lines, 0u);
}

TEST_F(MetricsTest, CalculateFileLoc_WithComments)
{
    auto path = create_file("comments.cpp", R"(
// Single line comment
#include <iostream>

/*
 * Block comment
 * spanning multiple lines
 */

int main() {
    // Another comment
    return 0;  // inline comment
}
)");

    auto metrics = calculate_file_loc(path);
    ASSERT_TRUE(metrics.has_value());

    EXPECT_GT(metrics->comment_lines, 0u);
    EXPECT_GT(metrics->code_lines, 0u);
}

TEST_F(MetricsTest, CalculateFileLoc_EmptyFile)
{
    auto path = create_file("empty.cpp", "");

    auto metrics = calculate_file_loc(path);
    ASSERT_TRUE(metrics.has_value());

    EXPECT_EQ(metrics->total_lines, 0u);
    EXPECT_EQ(metrics->code_lines, 0u);
    EXPECT_EQ(metrics->blank_lines, 0u);
}

TEST_F(MetricsTest, CalculateFileLoc_OnlyBlanks)
{
    auto path = create_file("blanks.cpp", "\n\n\n\n");

    auto metrics = calculate_file_loc(path);
    ASSERT_TRUE(metrics.has_value());

    EXPECT_EQ(metrics->total_lines, 4u);
    EXPECT_EQ(metrics->blank_lines, 4u);
    EXPECT_EQ(metrics->code_lines, 0u);
}

TEST_F(MetricsTest, CalculateFileLoc_NonexistentFile)
{
    auto metrics = calculate_file_loc("/nonexistent/file.cpp");
    EXPECT_FALSE(metrics.has_value());
}

TEST_F(MetricsTest, CalculateProjectLoc_MultipleFiles)
{
    auto file1 = create_file("a.cpp", "int a() { return 1; }\n");
    auto file2 = create_file("b.cpp", "int b() { return 2; }\nint c() { return 3; }\n");
    auto file3 = create_file("c.cpp", "// comment\nint d() { return 4; }\n");

    std::vector<std::filesystem::path> paths = {file1, file2, file3};
    auto project = calculate_project_loc(paths);

    EXPECT_EQ(project.total_files, 3u);
    EXPECT_EQ(project.files.size(), 3u);
    EXPECT_GT(project.total_lines, 0u);
    EXPECT_GT(project.total_code_lines, 0u);
}

TEST_F(MetricsTest, CalculateProjectLoc_EmptyList)
{
    std::vector<std::filesystem::path> paths;
    auto project = calculate_project_loc(paths);

    EXPECT_EQ(project.total_files, 0u);
    EXPECT_EQ(project.total_lines, 0u);
    EXPECT_TRUE(project.files.empty());
}

TEST_F(MetricsTest, CalculateProjectLoc_WithInvalidFile)
{
    auto valid = create_file("valid.cpp", "int x = 1;\n");
    std::vector<std::filesystem::path> paths = {valid, "/nonexistent.cpp"};

    auto project = calculate_project_loc(paths);

    // Should still process valid file
    EXPECT_EQ(project.total_files, 2u);  // Both counted
    EXPECT_EQ(project.files.size(), 1u);  // Only valid one has metrics
}

} // namespace aegis::test
