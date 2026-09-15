#include <cstdio>
#include <cstdlib>
#include "trigger_shortcuts.h"
#define CHECK(c) do { if (!(c)) { std::fprintf(stderr,"line %d: %s\n",__LINE__,#c); std::exit(1); } } while (0)
int main() {
    ShinkaTriggerShortcuts s;
    const unsigned left=s.view,right=s.speed,both=s.mask;
    CHECK(!s.poll(both,true) && !s.turbo); // held at launch is not a new press
    CHECK(!s.poll(0,true));
    CHECK(s.poll(left,true)==left && !s.turbo);
    for(int i=0;i<1000;++i) CHECK(!s.poll(left,true)); // no repeat at turbo cadence
    CHECK(s.poll(both,true)==right && s.turbo); // independent trigger edges
    CHECK(!s.poll(left,true) && s.turbo);
    CHECK(s.poll(both,true)==right && !s.turbo);
    CHECK(!s.poll(0,true));
    CHECK(s.poll(both,true)==both && s.turbo);
    CHECK(!s.poll(both,false) && !s.turbo); // focus loss/disabled context cancels
    CHECK(!s.poll(both,true) && !s.turbo); // still held on focus return
    CHECK(!s.poll(0,true));
    CHECK(s.poll(right,true)==right && s.turbo);
    s.reset(); // loading a state or closing a host menu
    CHECK(!s.turbo && !s.poll(right,true));
    CHECK(!s.poll(0,true));
    CHECK(!s.poll(0xfcff,true)); // every non-trigger button
    CHECK(s.poll(left,true)==left);
    std::puts("Trigger edges, independent holds, focus guards and state-load reset passed.");
}
