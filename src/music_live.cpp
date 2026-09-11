/* Music-only timbre substitution, on the emulator thread. The original SPU
 * still advances ADPCM, IRQs, pitch, ADSR, volumes and reverb. Nothing here
 * writes emulated state or reads files from the audio callback. */
#include "music_live.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <vector>

namespace {
constexpr uint32_t RAM = 512 * 1024;
constexpr float FADE = 1.0f / 2205.0f; // 50 ms at the SPU's 44100 Hz.
struct Wave { std::vector<int16_t> pcm; uint32_t loop = 0; bool looping = false; };
struct Sample { uint32_t offset = 0; float gain = 1; double rate = 1; std::array<Wave, 3> waves; };
struct Bank { std::vector<uint8_t> original; std::vector<Sample> samples; };
struct Voice {
    const Sample* sample = nullptr;
    const Bank* bank = nullptr;
    const uint8_t* ram = nullptr;
    uint32_t base = 0;
    bool identified = false;
    std::array<double, 3> phase{};
    std::array<float, 4> weights{1, 0, 0, 0};
};
std::vector<Bank> banks;
std::array<Voice, 24> voices;
int requested = 0;
bool written = false;
unsigned matched = 0;
char status[128] = "Original (music pack missing)";

uint32_t u32(std::istream& file) {
    unsigned char b[4];
    if (!file.read(reinterpret_cast<char*>(b), 4)) throw std::runtime_error("truncated music pack");
    return uint32_t(b[0]) | uint32_t(b[1]) << 8 | uint32_t(b[2]) << 16 | uint32_t(b[3]) << 24;
}
void check(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
float next(const Wave& wave, double& phase, double step) {
    const auto size = wave.pcm.size();
    if (phase >= size) {
        if (!wave.looping) return 0;
        phase = wave.loop + std::fmod(phase - wave.loop, double(size - wave.loop));
    }
    const auto i = static_cast<size_t>(phase);
    const auto j = i + 1 < size ? i + 1 : wave.looping ? wave.loop : i;
    const float fraction = static_cast<float>(phase - i);
    float value = wave.pcm[i] + (wave.pcm[j] - wave.pcm[i]) * fraction;
    phase += step;
    return value;
}
}

extern "C" void shinka_music_reset(void) {
    voices = {};
    matched = 0;
    written = false;
}
extern "C" void shinka_music_written(void) { written = true; }
extern "C" int shinka_music_available(void) { return !banks.empty(); }

extern "C" int shinka_music_load(const char* path) {
    shinka_music_reset();
    banks.clear();
    try {
        std::ifstream file(std::filesystem::u8path(path), std::ios::binary);
        check(bool(file), "music pack missing");
        char magic[8];
        check(bool(file.read(magic, 8)), "truncated music pack");
        const bool tuned = !std::memcmp(magic, "SHKMUS03", 8);
        const bool tagged = tuned || !std::memcmp(magic, "SHKMUS02", 8);
        check(tagged || !std::memcmp(magic, "SHKMUS01", 8), "unsupported music pack");
        check(u32(file) == 44100, "unsupported music rate");
        const auto count = u32(file);
        check(count > 0 && count <= 64, "invalid music bank count");
        std::vector<Bank> loaded;
        size_t total = 0;
        for (unsigned b = 0; b < count; ++b) {
            Bank bank;
            auto bytes = u32(file), samples = u32(file);
            check(bytes >= 16 && bytes <= RAM && samples > 0 && samples <= 256, "invalid music bank");
            bank.original.resize(bytes);
            check(bool(file.read(reinterpret_cast<char*>(bank.original.data()), bytes)), "truncated source fingerprint");
            for (unsigned s = 0; s < samples; ++s) {
                Sample sample;
                sample.offset = u32(file);
                check(sample.offset % 16 == 0 && sample.offset <= bytes - 16, "invalid sample offset");
                const auto role = tagged ? u32(file) : 0;
                check(role <= 2, "invalid music instrument role");
                // Apply to alternate timbres only, before the original SPU's
                // envelope/volume/reverb. Keep melody level and headroom intact.
                // Legacy packs carry no role information: never guess from pitch.
                sample.gain = role == 2 ? 0.707945784f : role == 1 ? 0.794328235f : 1.f;
                const auto ratio = tuned ? u32(file) : 65536u;
                check(ratio >= 2048 && ratio <= 2097152, "invalid music pitch ratio");
                sample.rate = double(ratio) / 65536.0;
                for (auto& wave : sample.waves) {
                    auto frames = u32(file), loop = u32(file);
                    check(frames > 0 && frames <= 132300 && (loop == 0xffffffff || loop < frames), "invalid replacement wave");
                    total += frames * 2;
                    check(total <= 256 * 1024 * 1024, "music pack exceeds memory budget");
                    wave.looping = loop != 0xffffffff;
                    wave.loop = wave.looping ? loop : 0;
                    wave.pcm.resize(frames);
                    // Pack is little endian; decode explicitly for host portability.
                    std::vector<unsigned char> raw(frames * 2);
                    check(bool(file.read(reinterpret_cast<char*>(raw.data()), raw.size())), "truncated replacement wave");
                    for (unsigned i = 0; i < frames; ++i)
                        wave.pcm[i] = static_cast<int16_t>(uint16_t(raw[2*i]) | uint16_t(raw[2*i+1]) << 8);
                }
                bank.samples.push_back(std::move(sample));
            }
            loaded.push_back(std::move(bank));
        }
        check(file.peek() == std::char_traits<char>::eof(), "trailing music data");
        banks = std::move(loaded);
        std::snprintf(status, sizeof(status), "Live instruments ready (%zu banks)", banks.size());
        std::fprintf(stdout, "Shinka music: %s\n", status);
        return 1;
    } catch (const std::exception& e) {
        std::snprintf(status, sizeof(status), "Original (%s)", e.what());
        std::fprintf(stderr, "Shinka music: %s\n", status);
        return 0;
    }
}

extern "C" void shinka_music_init(const char* executable) {
    try {
        auto path = std::filesystem::absolute(std::filesystem::u8path(executable)).parent_path() / "assets" / "music-live.bin";
        shinka_music_load(path.u8string().c_str());
    } catch (...) { std::snprintf(status, sizeof(status), "Original (music path unavailable)"); }
}

extern "C" void shinka_music_block(int palette) {
    requested = palette >= 0 && palette <= 3 && !banks.empty() ? palette : 0;
    if (written) {
        // A DMA/PIO upload can reuse a music bank before another KEYON. Never
        // keep substituting a voice whose sample memory has become something else.
        for (auto& voice : voices) {
            if (voice.bank && std::memcmp(voice.ram + voice.base,
                    voice.bank->original.data(), voice.bank->original.size())) {
                voice = {};
            }
        }
        written = false;
    }
}

extern "C" void shinka_music_key_on(int index, uint32_t address, const uint8_t* ram) {
    if (index < 0 || index >= 24) return;
    auto& voice = voices[index];
    voice = {};
    voice.identified = true;
    if (!ram || address > RAM - 16) return;
    // Match the whole bank at the inferred base, not just a drum sample which
    // might also occur in a sound-effect bank. Unknown/streaming voices pass through.
    for (const auto& bank : banks) for (const auto& sample : bank.samples) {
        if (address < sample.offset) continue;
        auto base = address - sample.offset;
        if (bank.original.size() > RAM - base) continue;
        if (std::memcmp(ram + address, bank.original.data() + sample.offset, 16)) continue;
        if (std::memcmp(ram + base, bank.original.data(), bank.original.size())) continue;
        voice.sample = &sample;
        voice.bank = &bank;
        voice.ram = ram;
        voice.base = base;
        voice.weights = {};
        voice.weights[requested] = 1;
        ++matched;
        return;
    }
}

extern "C" int16_t shinka_music_sample(int index, uint32_t address, uint32_t pitch,
                                        int16_t original, const uint8_t* ram, int noise) {
    if (index < 0 || index >= 24 || noise) return original;
    auto& voice = voices[index];
    // Re-identify active voices after a savestate; replacement phase restarts,
    // while the original SPU state and all subsequent note timing stay intact.
    if (!voice.identified) shinka_music_key_on(index, address, ram);
    if (!voice.sample) return original;
    float value = 0;
    const double step = double(pitch & 0x3fff) / 4096.0 * voice.sample->rate;
    const std::array<float, 4> samples{float(original),
        next(voice.sample->waves[0], voice.phase[0], step) * voice.sample->gain,
        next(voice.sample->waves[1], voice.phase[1], step) * voice.sample->gain,
        next(voice.sample->waves[2], voice.phase[2], step) * voice.sample->gain};
    for (int i = 0; i < 4; ++i) {
        const float target = i == requested ? 1.f : 0.f;
        // Equal progress of all weights keeps their sum at one, including
        // another selection during an unfinished fade.
        voice.weights[i] += (target - voice.weights[i]) * FADE * 5.f;
        value += voice.weights[i] * samples[i];
    }
    return static_cast<int16_t>(std::clamp(std::lround(value), -32768L, 32767L));
}

extern "C" const char* shinka_music_status(void) { return status; }
extern "C" unsigned shinka_music_matched_voices(void) { return matched; }
