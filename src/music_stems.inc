/* Included by music_live.cpp to share its exact-bank voice identification.
 * Samples remain independent; the offline tool joins key zones and duplicate
 * programs into instrument families using the owned VAB export metadata. */
namespace {
struct StemCapture {
    unsigned bank = 0, target = 0, frames = 0, unmatched = 0;
    std::vector<std::array<int32_t, 2>> sum;
    std::vector<std::vector<int32_t>> pcm;
    std::vector<uint32_t> offsets;
} stems;
constexpr size_t STEM_LIMIT = 256u * 1024u * 1024u;
}

extern "C" void shinka_music_stems_clear(void) { stems = {}; }
extern "C" int shinka_music_stems_begin(unsigned bank, unsigned frames) {
    if (stems.target || bank >= banks.size() || !frames || frames > 120u * 44100u) return 0;
    const auto count = banks[bank].samples.size();
    if (!count || size_t(frames) > STEM_LIMIT / (count * 2 * sizeof(int32_t))) return 0;
    try {
        StemCapture next;
        next.bank = bank; next.target = frames;
        next.sum.resize(count);
        next.pcm.resize(count);
        for (size_t i = 0; i < count; ++i) {
            next.pcm[i].resize(size_t(frames) * 2);
            next.offsets.push_back(banks[bank].samples[i].offset);
        }
        stems = std::move(next);
        return 1;
    } catch (...) { return 0; }
}
extern "C" int shinka_music_stems_active(void) { return stems.frames < stems.target; }
extern "C" unsigned shinka_music_stems_frames(void) { return stems.frames; }
extern "C" unsigned shinka_music_stems_samples(void) { return unsigned(stems.pcm.size()); }
extern "C" unsigned shinka_music_stems_unmatched(void) { return stems.unmatched; }

extern "C" void shinka_music_stems_voice(int index, int32_t left, int32_t right, int noise) {
    if (!shinka_music_stems_active() || index < 0 || index >= 24 || (!left && !right)) return;
    const auto& voice = voices[index];
    if (noise || !voice.sample || voice.bank != &banks[stems.bank]) {
        ++stems.unmatched;
        return;
    }
    const auto sample = size_t(voice.sample - voice.bank->samples.data());
    // Up to 24 signed-16-bit voice contributions fit comfortably in int32.
    stems.sum[sample][0] += left;
    stems.sum[sample][1] += right;
}
extern "C" void shinka_music_stems_frame(void) {
    if (!shinka_music_stems_active()) return;
    const size_t at = size_t(stems.frames) * 2;
    for (size_t i = 0; i < stems.pcm.size(); ++i) {
        stems.pcm[i][at] = stems.sum[i][0];
        stems.pcm[i][at + 1] = stems.sum[i][1];
        stems.sum[i] = {};
    }
    ++stems.frames;
}
extern "C" int shinka_music_stems_export(const char* directory) {
    if (!directory || !*directory || !stems.frames || shinka_music_stems_active()) return 0;
    try {
        const auto dir = std::filesystem::u8path(directory);
        if (!std::filesystem::is_directory(dir) || !std::filesystem::is_empty(dir)) return 0;
        for (size_t i = 0; i < stems.pcm.size(); ++i) {
            const auto path = dir / ("sample-" + std::to_string(stems.offsets[i]) + ".s32le");
            std::ofstream file(path, std::ios::binary);
            if (!file) return 0;
            // Explicit endian conversion in batches, outside the audio path.
            std::array<char, 16384> buffer;
            const size_t total = size_t(stems.frames) * 2;
            for (size_t at = 0; at < total;) {
                const size_t count = std::min(buffer.size() / 4, total - at);
                for (size_t j = 0; j < count; ++j) {
                    uint32_t value = uint32_t(stems.pcm[i][at + j]);
                    for (unsigned b = 0; b < 4; ++b) buffer[j * 4 + b] = char(value >> (8 * b));
                }
                file.write(buffer.data(), std::streamsize(count * 4));
                if (!file) return 0;
                at += count;
            }
        }
        return 1;
    } catch (...) { return 0; }
}
