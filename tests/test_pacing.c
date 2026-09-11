#include "pacing_sleep.h"
#include "frame_pacing.h"
#include <stdio.h>

static uint64_t clock_us, oversleep_us, sleep_total;
uint64_t SDL_GetPerformanceFrequency(void) { return 1000000u; }
uint64_t SDL_GetPerformanceCounter(void) { return clock_us++; }
void psx_host_sleep_micros(unsigned us) { sleep_total += us; clock_us += us + oversleep_us; }
void psx_host_sleep_ms(unsigned ms) { psx_host_sleep_micros(ms * 1000); }
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "Pacer failed line %d: %s\n", __LINE__, #x); return 1; } } while (0)

int main(void) {
    CHECK(shinka_pacing_sleep_us(100, 99, 1000000, 20000) == 0);
    CHECK(shinka_pacing_sleep_us(100, 100, 1000000, 20000) == 0);
    CHECK(shinka_pacing_sleep_us(0, 200, 1000000, 20000) == 0);
    CHECK(shinka_pacing_sleep_us(0, 201, 1000000, 20000) == 1);
    CHECK(shinka_pacing_sleep_us(0, 1000, 1000000, 20000) == 800);
    CHECK(shinka_pacing_sleep_us(0, 10000, 10000000, 200000) == 800);
    CHECK(shinka_pacing_sleep_us(0, UINT64_MAX, 1000000, 20000) == 19800);
    CHECK(shinka_pacing_sleep_us(0, UINT64_MAX, 1, UINT64_MAX) == 0);
    CHECK(shinka_pacing_sleep_us(0, 10000, 0, 20000) == 0);
    FramePacer p = {0};
    frame_pacer_wait(&p, 20.0);
    CHECK(p.next_deadline == 20000);
    for (int i = 1; i <= 500; ++i) {
        clock_us += 7000;
        frame_pacer_wait(&p, 20.0);
        CHECK(p.next_deadline == (uint64_t)(i + 1)*20000);
        CHECK(clock_us >= (uint64_t)i*20000 && clock_us < (uint64_t)i*20000 + 10);
    }
    CHECK(sleep_total > 6000000);
    /* Late OS wakes preserve the original deadline; catch-up must not drift
     * or forgive audio debt on every slightly late frame. */
    oversleep_us = 1500;
    for (int i = 501; i <= 1000; ++i) {
        clock_us += 7000;
        frame_pacer_wait(&p, 20.0);
        CHECK(p.next_deadline == (uint64_t)(i + 1)*20000);
    }
    uint64_t before = p.next_deadline;
    clock_us = before + 40000;
    frame_pacer_wait(&p, 20.0);
    CHECK(p.next_deadline == before + 20000);
    clock_us = p.next_deadline + 260000;
    uint64_t reanchor = clock_us;
    frame_pacer_wait(&p, 20.0);
    CHECK(p.next_deadline == reanchor + 20000);
    puts("Pacer deadlines, short sleeps, late wakes and bounded catch-up passed.");
    return 0;
}
