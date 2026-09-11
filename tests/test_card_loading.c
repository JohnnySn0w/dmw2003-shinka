#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); exit(1); } } while (0)
uint32_t shinka_card_read_size(uint32_t, uint32_t, int);
uint32_t shinka_card_read_completed(uint32_t, uint32_t, uint32_t);
int main(void) {
    uint32_t total;
    /* Every request covers exactly the original sector-rounded range, with
     * no gaps or extra sectors, including non-aligned save payload lengths. */
    for (total = 1; total <= 131072; ++total) {
        uint32_t done = 0, count = 0;
        uint32_t rounded = (total + 127u) & ~127u;
        while (done < total) {
            uint32_t size = shinka_card_read_size(total, done, 1);
            CHECK(size >= 128 && size <= 1024 && !(size & 127));
            CHECK(size <= rounded - done);
            CHECK(shinka_card_read_completed(total, done, size) == size);
            if (!done) CHECK(size == 128);
            CHECK(shinka_card_read_size(total, done, 0) == 128);
            done += size;
            ++count;
        }
        CHECK(done == rounded);
        if (total == 9984) CHECK(count == 11);
    }
    CHECK(shinka_card_read_size(9984, 9344, 1) == 640);
    CHECK(shinka_card_read_size(9984, 0, 1) == 128);
    CHECK(shinka_card_read_size(9984, 9984, 1) == 128);
    CHECK(shinka_card_read_size(9984, 0xffffffff, 1) == 128);
    CHECK(shinka_card_read_size(131200, 128, 1) == 128);
    CHECK(shinka_card_read_size(129, 128, 1) == 128);
    CHECK(shinka_card_read_size(0x26c4, 128, 1) == 1024);
    CHECK(shinka_card_read_size(1024, 129, 1) == 128);
    /* Old in-flight single-sector states and a restored larger request are
     * both accounted by their actual size, regardless of current policy. */
    CHECK(shinka_card_read_completed(9984, 128, 128) == 128);
    CHECK(shinka_card_read_completed(9984, 128, 1024) == 1024);
    CHECK(shinka_card_read_completed(9984, 128, 129) == 128);
    CHECK(shinka_card_read_completed(9984, 9728, 1024) == 128);
    CHECK(shinka_card_read_completed(9984, 9984, 1024) == 128);
    return 0;
}
