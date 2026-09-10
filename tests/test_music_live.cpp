#include "music_live.h"
#include <array>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <vector>
#define CHECK(x) do { if (!(x)) { std::fprintf(stderr,"line %d: %s\n",__LINE__,#x); return 1; } } while(0)
static void u32(std::ofstream& f, unsigned value) {
    char b[4] = {char(value),char(value>>8),char(value>>16),char(value>>24)};
    f.write(b,4);
}
static void fixture(const std::filesystem::path& path) {
    std::ofstream f(path,std::ios::binary);
    f.write("SHKMUS01",8); u32(f,44100); u32(f,1); u32(f,32); u32(f,1);
    for(int i=0;i<32;i++) f.put(char(i+1));
    u32(f,16);
    for(int p=1;p<=3;p++) {
        u32(f,4); u32(f,0);
        for(int i=0;i<4;i++) { int v=p*1000+i*100; f.put(char(v)); f.put(char(v>>8)); }
    }
}
int main() {
    auto path = std::filesystem::temp_directory_path()/"shinka-music-live-test.bin";
    fixture(path);
    CHECK(shinka_music_load(path.u8string().c_str()));
    std::vector<uint8_t> ram(512*1024);
    for(int i=0;i<32;i++) ram[1024+i]=uint8_t(i+1);
    auto before = ram;
    shinka_music_block(2);
    shinka_music_key_on(0,1040,ram.data());
    CHECK(shinka_music_matched_voices()==1);
    CHECK(shinka_music_sample(0,1040,4096,700,ram.data(),0)==2000);
    CHECK(shinka_music_sample(0,1040,4096,700,ram.data(),0)==2100);
    CHECK(shinka_music_sample(0,1040,0,700,ram.data(),0)==2200);
    CHECK(shinka_music_sample(0,1040,0,700,ram.data(),0)==2200);
    CHECK(shinka_music_sample(0,1040,8192,700,ram.data(),0)==2200);
    CHECK(shinka_music_sample(0,1040,4096,700,ram.data(),0)==2000);
    // Every palette's cursor advanced while inaudible. Live changes never
    // restart the score, and rapid successive switches stay bounded.
    for(int p : {3,1,0,2,0}) {
        shinka_music_block(p);
        for(int i=0;i<5000;i++) {
            int s=shinka_music_sample(0,1040,4096,700,ram.data(),0);
            CHECK(s>=699 && s<=3300);
        }
    }
    CHECK(shinka_music_sample(0,1040,4096,700,ram.data(),0)==700);
    CHECK(shinka_music_sample(0,1040,4096,-1234,ram.data(),1)==-1234);
    ram[1024]=99;
    shinka_music_written();
    shinka_music_block(2);
    CHECK(shinka_music_sample(0,1040,4096,456,ram.data(),0)==456);
    // A matching sample inside an unrelated bank must remain original.
    ram[1024]=99;
    shinka_music_key_on(1,1040,ram.data());
    shinka_music_block(3);
    CHECK(shinka_music_sample(1,1040,4096,999,ram.data(),0)==999);
    ram[1024]=1;
    CHECK(ram==before);
    shinka_music_reset();
    CHECK(shinka_music_matched_voices()==0);
    CHECK(shinka_music_sample(0,1040,4096,0,ram.data(),0)==3000);
    CHECK(shinka_music_matched_voices()==1);
    // Invalid assets fail back to original without leaving dangling voices.
    std::ofstream(path,std::ios::binary).write("SHKMUS01",8);
    CHECK(!shinka_music_load(path.u8string().c_str()));
    CHECK(!shinka_music_available());
    CHECK(shinka_music_sample(0,1040,4096,555,ram.data(),0)==555);
    std::filesystem::remove(path);
    std::puts("Live music: palette switching, pitch/loops, noise, exact-bank isolation, state reset and corrupt-pack fallback passed.");
    return 0;
}
