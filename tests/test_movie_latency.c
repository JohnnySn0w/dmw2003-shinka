#include "latency_ring.h"
#include <stdio.h>
#include <string.h>

static uint64_t now;
uint64_t SDL_GetPerformanceFrequency(void) { return 1000000; }
uint64_t SDL_GetPerformanceCounter(void) { return now; }
static char output[1024*1024];
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"Failed: %s\n",#x); return 1; } } while (0)
int main(void) {
    for (int i=0; i<4200; ++i) {
        now=1000000+(uint64_t)i*20000;
        latency_ring_frame_begin();
        now+=3000;
        latency_ring_mark(LAT_PACED);
        now+=20;
        latency_ring_restamp_input();
        now+=500;
        latency_ring_mark(LAT_SWAP_BEGIN);
        now+=100;
        latency_ring_mark(LAT_SWAP_END);
    }
    int length=latency_ring_dump_json(output,sizeof(output),4096);
    CHECK(length>0 && length<(int)sizeof(output));
    CHECK(strstr(output,"\"f\":104,\"begin\":0.0,\"input\":3020.0,\"paced\":3000.0")!=NULL);
    CHECK(strstr(output,"\"f\":4199,")!=NULL);
    CHECK(output[0]=='[' && output[length-1]==']');
    int count=0;
    const char *p=output;
    while ((p=strstr(p,"\"f\":"))!=NULL) { ++count; ++p; }
    CHECK(count==4096);
    return 0;
}
