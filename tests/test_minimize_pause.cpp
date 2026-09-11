#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#define CHECK(c) do { if (!(c)) { std::fprintf(stderr,"line %d: %s\n",__LINE__,#c); std::exit(1); } } while (0)
enum { SDL_WINDOW_MINIMIZED=1, SDL_QUIT=2, SDL_CONTROLLERDEVICEREMOVED=3, SDL_CONTROLLERDEVICEADDED=4 };
struct SDL_Event { int type; };
struct FramePacer { uint64_t next_deadline; };
struct Player { void* handle; int rumble_small,rumble_large; bool rumble_known; };
static Player g_players[1];
static bool g_headless;
static void* sdl_window=(void*)1;
static unsigned flags,delays,beats,guards,rumbles,refreshes,closes,event_index;
static int netplay;
static FramePacer s_frame_pacer;
static uint64_t s_fps_last_time;
uint64_t s_frame_count=1234;
static int g_audio_unmute_resync,sdl_audio_fadein_left;
static const int sdl_audio_fade_samples=441;
static int psx_netplay_active() { return netplay; }
static unsigned SDL_GetWindowFlags(void*) { return flags; }
static int SDL_GameControllerRumble(void*,int a,int b,int duration) {
    CHECK(!a && !b && !duration); ++rumbles; return 0;
}
static int SDL_PollEvent(SDL_Event* ev) {
    const int events[]={SDL_CONTROLLERDEVICEADDED,SDL_CONTROLLERDEVICEREMOVED,99};
    if(event_index==3) return 0;
    ev->type=events[event_index++];return 1;
}
static void close_controller() { ++closes; }
static void refresh_player_devices() { ++refreshes; }
static void psx_crash_trace_set_exit_origin(const char*) {}
static void shutdown_runtime() { CHECK(false); }
static void starvation_watchdog_heartbeat() { ++beats; }
static void SDL_Delay(unsigned ms) {
    CHECK(ms==50 && s_frame_count==1234);
    if(++delays==2) flags=0;
}
static void savestate_input_guard_arm() { ++guards; }
#include "minimize_pause.inc"

static void fixture() {
    g_headless=false;sdl_window=(void*)1;netplay=0;flags=SDL_WINDOW_MINIMIZED;
    delays=beats=guards=rumbles=refreshes=closes=event_index=0;
    s_frame_pacer.next_deadline=123;s_fps_last_time=456;
    g_audio_unmute_resync=sdl_audio_fadein_left=0;
    g_players[0]={(void*)1,1,255,true};
}
static void control(const char* value) {
#ifdef _WIN32
    _putenv_s("SHINKA_PAUSE_MINIMIZED",value);
#else
    setenv("SHINKA_PAUSE_MINIMIZED",value,1);
#endif
}
int main() {
    control("1");fixture();shinka_minimize_wait();
    CHECK(delays==2 && beats==2 && guards==1 && rumbles==1);
    CHECK(refreshes==2 && closes==1 && event_index==3);
    CHECK(s_frame_count==1234 && !s_frame_pacer.next_deadline && !s_fps_last_time);
    CHECK(g_audio_unmute_resync && sdl_audio_fadein_left==sdl_audio_fade_samples);
    CHECK(!g_players[0].rumble_known && !g_players[0].rumble_large);
    for(unsigned scenario=0;scenario<5;++scenario) {
        fixture();
        if(scenario==0) flags=0; // visible, including unfocused windows
        if(scenario==1) g_headless=true;
        if(scenario==2) sdl_window=nullptr;
        if(scenario==3) netplay=1;
        if(scenario==4) control("0");
        shinka_minimize_wait();
        CHECK(!delays && !beats && !guards && !rumbles && !refreshes);
        CHECK(s_frame_pacer.next_deadline==123 && s_fps_last_time==456);
    }
    control("");
    std::puts("Minimized suspension, restore, device events and bypass guards passed.");
}
