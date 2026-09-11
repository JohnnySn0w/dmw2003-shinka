#include "music_live.h"
#include <array>
#include <cmath>
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
static void fixture(const std::filesystem::path& path, int role = -1, int ratio = -1) {
    std::ofstream f(path,std::ios::binary);
    f.write(ratio >= 0 ? "SHKMUS03" : role < 0 ? "SHKMUS01" : "SHKMUS02",8); u32(f,44100); u32(f,1); u32(f,32); u32(f,1);
    for(int i=0;i<32;i++) f.put(char(i+1));
    u32(f,16);
    if(role >= 0) u32(f,unsigned(role));
    if(ratio >= 0) u32(f,unsigned(ratio));
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
    CHECK(shinka_music_meter_begin(1));
    shinka_music_meter_voice(0,500,-500,0); // old pack has no trustworthy role
    shinka_music_meter_voice(-1,1000,1000,0);
    shinka_music_meter_voice(24,1000,1000,0);
    shinka_music_meter_frame();
    CHECK(shinka_music_meter_rms(3)==500 && shinka_music_meter_rms(0)==0);
    CHECK(shinka_music_meter_begin(0));
    CHECK(!shinka_music_meter_active() && shinka_music_meter_frames()==0);
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
    // Tagged roles change only alternate output gain, never the original,
    // cursor progression, or unrelated/noise voices. Legacy packs above retain
    // their old levels because they contain no reliable instrument roles.
    for(int role=0;role<=2;role++) {
        fixture(path,role);
        CHECK(shinka_music_load(path.u8string().c_str()));
        const float gain=role==2 ? 0.707945784f : role==1 ? 0.794328235f : 1.f;
        for(int palette=0;palette<=3;palette++) {
            shinka_music_block(palette);
            shinka_music_key_on(0,1040,ram.data());
            for(int i=0;i<6;i++) {
                int expected=palette ? int((palette*1000+(i%4)*100)*gain+0.5f) : 700;
                CHECK(shinka_music_sample(0,1040,4096,700,ram.data(),0)==expected);
            }
        }
        shinka_music_block(0);
        for(int i=0;i<10000;i++) shinka_music_sample(0,1040,4096,700,ram.data(),0);
        CHECK(shinka_music_sample(0,1040,4096,700,ram.data(),0)==700);
        CHECK(shinka_music_sample(0,1040,4096,-1234,ram.data(),1)==-1234);
        // Meter the role's summed stereo bus, including phase cancellation and
        // silent frames. Noise and unrecognized voices remain unclassified.
        CHECK(shinka_music_meter_begin(2));
        shinka_music_meter_voice(0,300,-400,0);
        shinka_music_meter_voice(0,-100,100,0);
        shinka_music_meter_frame();
        shinka_music_meter_voice(0,600,800,1);
        shinka_music_meter_voice(1,-600,-800,0);
        shinka_music_meter_frame();
        CHECK(!shinka_music_meter_active() && shinka_music_meter_frames()==2);
        CHECK(std::abs(shinka_music_meter_rms(role)-std::sqrt(130000.0/4))<.0001);
        CHECK(shinka_music_meter_peak(role)==300 && shinka_music_meter_rms(3)==0);
        // Bounded measurement freezes exactly at its requested frame count.
        shinka_music_meter_voice(0,32767,32767,0);shinka_music_meter_frame();
        CHECK(shinka_music_meter_frames()==2 && shinka_music_meter_peak(role)==300);
        CHECK(!shinka_music_meter_begin(1323001));
        CHECK(shinka_music_meter_frames()==2);
        CHECK(shinka_music_meter_begin(1));
        shinka_music_meter_voice(1,600,800,0);shinka_music_meter_frame();
        CHECK(std::abs(shinka_music_meter_rms(3)-std::sqrt(500000.0))<.0001);
        CHECK(shinka_music_meter_peak(3)==800 && shinka_music_meter_peak(99)==0);
        CHECK(shinka_music_meter_begin(10));shinka_music_reset();
        CHECK(!shinka_music_meter_active() && shinka_music_meter_frames()==0);
        // Metering never changes the replacement sample stream or its phase.
        for(int palette=0;palette<4;++palette) {
            std::array<int16_t,16> baseline{};
            shinka_music_block(palette);shinka_music_key_on(0,1040,ram.data());
            for(auto& s:baseline) s=shinka_music_sample(0,1040,4096,700,ram.data(),0);
            shinka_music_key_on(0,1040,ram.data());CHECK(shinka_music_meter_begin(16));
            for(auto s:baseline) {
                auto observed=shinka_music_sample(0,1040,4096,700,ram.data(),0);
                CHECK(observed==s);
                shinka_music_meter_voice(0,observed,-observed,0);shinka_music_meter_frame();
            }
        }
        CHECK(ram==before);
    }
    // A root two octaves above the rendered reference compensates a quarter-
    // rate guest note. Preserve pitch, loop progression and Original output.
    fixture(path,0,4*65536);
    CHECK(shinka_music_load(path.u8string().c_str()));
    for(int p=0;p<=3;++p) {
        shinka_music_block(p);shinka_music_key_on(0,1040,ram.data());
        for(int i=0;i<12;++i)
            CHECK(shinka_music_sample(0,1040,1024,700,ram.data(),0)==(p ? p*1000+(i%4)*100 : 700));
    }
    for(int ratio : {0,2047,2097153}) {
        fixture(path,0,ratio);
        CHECK(!shinka_music_load(path.u8string().c_str()));
        CHECK(shinka_music_sample(0,1040,1024,555,ram.data(),0)==555);
    }
    fixture(path,3);
    CHECK(!shinka_music_load(path.u8string().c_str()));
    CHECK(!shinka_music_available());
    // Invalid assets fail back to original without leaving dangling voices.
    std::ofstream(path,std::ios::binary).write("SHKMUS01",8);
    CHECK(!shinka_music_load(path.u8string().c_str()));
    CHECK(!shinka_music_available());
    CHECK(shinka_music_sample(0,1040,4096,555,ram.data(),0)==555);
    std::filesystem::remove(path);
    std::puts("Live music: palette switching, pitch/loops, noise, exact-bank isolation, state reset and corrupt-pack fallback passed.");
    return 0;
}
