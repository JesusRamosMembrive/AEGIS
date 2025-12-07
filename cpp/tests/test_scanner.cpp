#include "../src/scanner.hpp"

#include <gtest/gtest.h>
#include <filesystem>
#include <fstream>

namespace aegis::test {

class ScannerTest : public ::testing::Test {
protected:
    void SetUp() override
    {
        // Create temporary test directory structure
        test_dir_ = std::filesystem::temp_directory_path() / "aegis_test_scanner";
        std::filesystem::remove_all(test_dir_);
        std::filesystem::create_directories(test_dir_);

        // Create test files
        create_file(test_dir_ / "main.cpp", "int main() { return 0; }");
        create_file(test_dir_ / "helper.hpp", "#pragma once\nvoid helper();");
        create_file(test_dir_ / "readme.md", "# README");

        // Create subdirectory with files
        auto sub_dir = test_dir_ / "src";
        std::filesystem::create_directories(sub_dir);
        create_file(sub_dir / "utils.cpp", "void utils() {}");
        create_file(sub_dir / "utils.h", "#pragma once");

        // Create excluded directory
        auto node_modules = test_dir_ / "node_modules";
        std::filesystem::create_directories(node_modules);
        create_file(node_modules / "package.cpp", "// should be ignored");

        // Create hidden directory
        auto hidden = test_dir_ / ".hidden";
        std::filesystem::create_directories(hidden);
        create_file(hidden / "secret.cpp", "// should be ignored");
    }

    void TearDown() override
    {
        std::filesystem::remove_all(test_dir_);
    }

    static void create_file(const std::filesystem::path& path, const std::string& content)
    {
        std::ofstream file(path);
        file << content;
    }

    std::filesystem::path test_dir_;
};

TEST_F(ScannerTest, ScanFindsCorrectFiles)
{
    ScannerConfig config;
    config.root = test_dir_;
    config.extensions = {".cpp", ".hpp", ".h"};

    Scanner scanner(std::move(config));
    auto files = scanner.scan();

    // Should find: main.cpp, helper.hpp, src/utils.cpp, src/utils.h
    // Should NOT find: readme.md, node_modules/package.cpp, .hidden/secret.cpp
    EXPECT_EQ(files.size(), 4u);

    // Verify paths (sorted)
    std::vector<std::string> filenames;
    for (const auto& f : files) {
        filenames.push_back(f.path.filename().string());
    }

    EXPECT_TRUE(std::find(filenames.begin(), filenames.end(), "main.cpp") != filenames.end());
    EXPECT_TRUE(std::find(filenames.begin(), filenames.end(), "helper.hpp") != filenames.end());
    EXPECT_TRUE(std::find(filenames.begin(), filenames.end(), "utils.cpp") != filenames.end());
    EXPECT_TRUE(std::find(filenames.begin(), filenames.end(), "utils.h") != filenames.end());
}

TEST_F(ScannerTest, ScanExcludesNodeModules)
{
    ScannerConfig config;
    config.root = test_dir_;
    config.extensions = {".cpp"};

    Scanner scanner(std::move(config));
    auto files = scanner.scan();

    for (const auto& f : files) {
        EXPECT_TRUE(f.path.string().find("node_modules") == std::string::npos)
            << "Should not include files from node_modules: " << f.path;
    }
}

TEST_F(ScannerTest, ScanExcludesHiddenDirs)
{
    ScannerConfig config;
    config.root = test_dir_;
    config.extensions = {".cpp"};

    Scanner scanner(std::move(config));
    auto files = scanner.scan();

    for (const auto& f : files) {
        EXPECT_TRUE(f.path.string().find(".hidden") == std::string::npos)
            << "Should not include files from hidden directories: " << f.path;
    }
}

TEST_F(ScannerTest, ScanWithCustomExtensions)
{
    ScannerConfig config;
    config.root = test_dir_;
    config.extensions = {".md"};

    Scanner scanner(std::move(config));
    auto files = scanner.scan();

    EXPECT_EQ(files.size(), 1u);
    EXPECT_EQ(files[0].path.filename(), "readme.md");
}

TEST_F(ScannerTest, ScanNonexistentDir)
{
    ScannerConfig config;
    config.root = "/nonexistent/path";
    config.extensions = {".cpp"};

    Scanner scanner(std::move(config));
    auto files = scanner.scan();

    EXPECT_TRUE(files.empty());
}

TEST_F(ScannerTest, ConfigAccessor)
{
    ScannerConfig config;
    config.root = test_dir_;
    config.extensions = {".cpp", ".hpp"};

    Scanner scanner(std::move(config));
    const auto& returned_config = scanner.config();

    EXPECT_EQ(returned_config.root, test_dir_);
    EXPECT_EQ(returned_config.extensions.size(), 2u);
}

} // namespace aegis::test
