#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <windows.h>

int main(int argc, char** argv) {
    if (argc != 2 || GetACP() != CP_UTF8) return 1;
    // These are the runtime's two file-I/O paths: C++ configuration/assets and
    // C memory-card writes. Verify a real roundtrip through the command line.
    const std::filesystem::path folder(argv[1]);
    if (folder.filename().u16string() != u"Jos\u00e9 \u9032\u5316") return 5;
    std::filesystem::create_directories(folder);
    const auto file = folder / "roundtrip.txt";
    const std::string narrow = file.string();
    FILE* stream = std::fopen(narrow.c_str(), "wb");
    if (!stream) return 2;
    const bool written = std::fputs("preserved", stream) >= 0;
    const bool closed = std::fclose(stream) == 0;
    if (!written || !closed) return 3;
    std::ifstream input(file);
    std::string content;
    input >> content;
    input.close();
    if (content != "preserved") return 4;
    std::filesystem::remove(file);
    std::cout << "UTF-8 command-line, filesystem and card-style I/O passed\n";
}
