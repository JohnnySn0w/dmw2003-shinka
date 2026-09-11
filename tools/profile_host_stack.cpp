// Windows x64 diagnostic sampler. Use only an isolated Shinka test process.
// Copy the thread context and stack while stopped; unwind AFTER resuming it.
// This measures sampled residency, not CPU time. Never benchmark with it running.
#define NOMINMAX
#include <windows.h>
#include <dbghelp.h>
#include <tlhelp32.h>
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

struct Handle {
    HANDLE value;
    explicit Handle(HANDLE h) : value(h) {
        if (!h || h == INVALID_HANDLE_VALUE) throw std::runtime_error("Open handle failed");
    }
    ~Handle() { CloseHandle(value); }
    Handle(const Handle&) = delete;
    Handle& operator=(const Handle&) = delete;
};

// Never keep the target stopped while accessing symbols, allocating or printing.
struct Suspension {
    HANDLE thread;
    explicit Suspension(HANDLE h) : thread(h) {
        if (SuspendThread(thread) == DWORD(-1)) throw std::runtime_error("SuspendThread failed");
    }
    ~Suspension() {
        if (ResumeThread(thread) == DWORD(-1)) {
            std::fprintf(stderr, "ERROR: ResumeThread failed (%lu)\n", GetLastError());
            std::abort();
        }
    }
};

struct Module { DWORD64 base; DWORD size; DWORD timestamp; std::string path; };
struct Sample { std::vector<DWORD64> pcs; double stop_us; bool truncated; };
static std::vector<unsigned char> stack_bytes(256 * 1024);
static DWORD64 stack_region_low, stack_low, stack_high;
static SIZE_T stack_size;

static BOOL CALLBACK read_snapshot(HANDLE process, DWORD64 address, PVOID dest,
                                  DWORD count, LPDWORD got) {
    *got = 0;
    if ((address >= stack_region_low && address < stack_high) ||
        (address < stack_region_low && count > stack_region_low - address)) {
        // Refuse live reads beyond the copied stack: the thread is running now.
        if (address < stack_low || address - stack_low > stack_size || count > stack_size - (address - stack_low)) return FALSE;
        std::memcpy(dest, stack_bytes.data() + (address - stack_low), count);
        *got = count;
        return TRUE;
    }
    SIZE_T read = 0;
    BOOL ok = ReadProcessMemory(process, reinterpret_cast<LPCVOID>(address), dest, count, &read);
    *got = static_cast<DWORD>(read);
    return ok;
}

static unsigned long long thread_cpu(HANDLE thread) {
    FILETIME created{}, exited{}, kernel{}, user{};
    if (!GetThreadTimes(thread, &created, &exited, &kernel, &user))
        throw std::runtime_error("GetThreadTimes failed");
    return ((static_cast<unsigned long long>(kernel.dwHighDateTime) << 32) | kernel.dwLowDateTime)
         + ((static_cast<unsigned long long>(user.dwHighDateTime) << 32) | user.dwLowDateTime);
}

static Sample capture(HANDLE process, HANDLE thread) {
    CONTEXT context{};
    context.ContextFlags = CONTEXT_FULL;
    MEMORY_BASIC_INFORMATION region{};
    BOOL ok = FALSE;
    auto start = std::chrono::steady_clock::now();
    {
        Suspension stopped(thread);
        if (GetThreadContext(thread, &context) &&
            VirtualQueryEx(process, reinterpret_cast<LPCVOID>(context.Rsp), &region, sizeof(region))) {
            stack_low = context.Rsp;
            stack_region_low = reinterpret_cast<DWORD64>(region.BaseAddress);
            stack_high = reinterpret_cast<DWORD64>(region.BaseAddress) + region.RegionSize;
            stack_size = 0;
            SIZE_T wanted = static_cast<SIZE_T>(std::min<DWORD64>(stack_high - stack_low, stack_bytes.size()));
            ok = ReadProcessMemory(process, reinterpret_cast<LPCVOID>(stack_low), stack_bytes.data(), wanted, &stack_size);
        }
    }
    auto resumed = std::chrono::steady_clock::now();
    if (!ok) throw std::runtime_error("Context/stack snapshot failed (target has been resumed)");
    Sample sample{{context.Rip}, std::chrono::duration<double, std::micro>(resumed-start).count(), false};
    STACKFRAME64 frame{};
    frame.AddrPC.Offset = context.Rip;
    frame.AddrFrame.Offset = context.Rbp;
    frame.AddrStack.Offset = context.Rsp;
    frame.AddrPC.Mode = frame.AddrFrame.Mode = frame.AddrStack.Mode = AddrModeFlat;
    DWORD64 prior_pc = 0, prior_sp = 0;
    for (int i = 0; i < 64; ++i) {
        if (!StackWalk64(IMAGE_FILE_MACHINE_AMD64, process, thread, &frame, &context,
                         read_snapshot, SymFunctionTableAccess64, SymGetModuleBase64, nullptr) || !frame.AddrPC.Offset) break;
        if (frame.AddrPC.Offset == prior_pc && frame.AddrStack.Offset == prior_sp) break;
        if (i != 0 || frame.AddrPC.Offset != sample.pcs.front()) sample.pcs.push_back(frame.AddrPC.Offset);
        prior_pc = frame.AddrPC.Offset;
        prior_sp = frame.AddrStack.Offset;
        if (i == 63) sample.truncated = true;
    }
    return sample;
}

static std::string escaped(const std::string& input) {
    std::string result;
    for (unsigned char c : input) {
        if (c == '\\' || c == '"') result += '\\';
        if (c >= 32) result += static_cast<char>(c);
    }
    return result;
}

int main(int argc, char** argv) {
    try {
        if (argc != 5) throw std::runtime_error("Usage: profile_host_stack PID TID SECONDS OUTPUT.json (isolated test process only)");
        DWORD pid = std::stoul(argv[1]), tid = std::stoul(argv[2]);
        double seconds = std::stod(argv[3]);
        if (seconds < 1 || seconds > 60 || pid == GetCurrentProcessId()) throw std::runtime_error("Invalid target/duration");
        if (GetFileAttributesA(argv[4]) != INVALID_FILE_ATTRIBUTES) throw std::runtime_error("Output already exists");
        Handle process(OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid));
        Handle thread(OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, FALSE, tid));
        if (GetProcessIdOfThread(thread.value) != pid) throw std::runtime_error("Thread belongs to another process");
        char target[MAX_PATH]{}; DWORD target_length = MAX_PATH;
        if (!QueryFullProcessImageNameA(process.value, 0, target, &target_length) ||
            std::string(target).find("dmw2003-shinka.exe") == std::string::npos)
            throw std::runtime_error("Target must be the isolated dmw2003-shinka.exe test runner");
        // Explicit local-only search path avoids symbol-server requests or credentials.
        SymSetOptions(SYMOPT_DEFERRED_LOADS | SYMOPT_FAIL_CRITICAL_ERRORS | SYMOPT_NO_PROMPTS | SYMOPT_IGNORE_NT_SYMPATH);
        if (!SymInitialize(process.value, ".", FALSE)) throw std::runtime_error("SymInitialize failed");
        std::vector<Module> modules;
        Handle snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid));
        MODULEENTRY32 entry{}; entry.dwSize = sizeof(entry);
        if (!Module32First(snapshot.value, &entry)) throw std::runtime_error("Module enumeration failed");
        do {
            auto base = reinterpret_cast<DWORD64>(entry.modBaseAddr);
            IMAGE_DOS_HEADER dos{}; IMAGE_NT_HEADERS64 nt{}; SIZE_T got = 0;
            if (!ReadProcessMemory(process.value, entry.modBaseAddr, &dos, sizeof(dos), &got) ||
                dos.e_magic != IMAGE_DOS_SIGNATURE || dos.e_lfanew < 0 ||
                !ReadProcessMemory(process.value, entry.modBaseAddr + dos.e_lfanew, &nt, sizeof(nt), &got) ||
                nt.Signature != IMAGE_NT_SIGNATURE)
                throw std::runtime_error("Cannot verify loaded module PE header");
            modules.push_back({base, entry.modBaseSize, nt.FileHeader.TimeDateStamp, entry.szExePath});
            SymLoadModuleEx(process.value, nullptr, entry.szExePath, nullptr, base, entry.modBaseSize, nullptr, 0);
        } while (Module32Next(snapshot.value, &entry));
        // Prime unwind tables before timing. All symbol work occurs after resuming.
        capture(process.value, thread.value);
        Handle timer(CreateWaitableTimerExW(nullptr, nullptr, 2, TIMER_ALL_ACCESS));
        auto start = std::chrono::steady_clock::now();
        auto before_cpu = thread_cpu(thread.value);
        std::vector<Sample> samples;
        samples.reserve(static_cast<size_t>(seconds * 250));
        unsigned random = 0x91287u;
        while (std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count() < seconds) {
            samples.push_back(capture(process.value, thread.value));
            random = random * 1664525u + 1013904223u;
            LARGE_INTEGER delay{}; delay.QuadPart = -static_cast<LONGLONG>(30000 + random % 40001); // 3..7 ms; avoid frame aliasing.
            if (!SetWaitableTimer(timer.value, &delay, 0, nullptr, nullptr, FALSE) ||
                WaitForSingleObject(timer.value, INFINITE) != WAIT_OBJECT_0)
                throw std::runtime_error("Sampler timer failed");
        }
        auto after_cpu = thread_cpu(thread.value);
        double wall = std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        std::ofstream out(argv[4]);
        if (!out) throw std::runtime_error("Cannot create output");
        out << "{\"schema\":1,\"pid\":" << pid << ",\"tid\":" << tid << ",\"wall_seconds\":" << wall
            << ",\"thread_cpu_seconds\":" << (after_cpu-before_cpu)/10000000.0 << ",\"modules\":[";
        for (size_t i = 0; i < modules.size(); ++i) {
            if (i) out << ',';
            out << "{\"base\":" << modules[i].base << ",\"size\":" << modules[i].size
                << ",\"timestamp\":" << modules[i].timestamp
                << ",\"path\":\"" << escaped(modules[i].path) << "\"}";
        }
        out << "],\"samples\":[";
        for (size_t i = 0; i < samples.size(); ++i) {
            if (i) out << ',';
            out << "{\"stop_us\":" << samples[i].stop_us << ",\"truncated\":" << (samples[i].truncated ? "true" : "false") << ",\"pcs\":[";
            for (size_t j = 0; j < samples[i].pcs.size(); ++j) { if (j) out << ','; out << samples[i].pcs[j]; }
            out << "]}";
        }
        out << "]}\n";
        if (!out) throw std::runtime_error("Writing output failed");
        SymCleanup(process.value);
        std::cout << "Recorded " << samples.size() << " stacks; target resumed before every unwind.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << " (Windows error " << GetLastError() << ")\n";
        return 1;
    }
}
