#include <stdint.h>
#include <stdio.h>
#include <string.h>

static uint8_t ram[2 * 1024 * 1024];
static int available = 1;
uint8_t *memory_get_ram_ptr(void) { return available ? ram : NULL; }
extern int shinka_overlay_code_matches(const uint32_t *, uint32_t, uint32_t);
#define CHECK(expr) do { if (!(expr)) { fprintf(stderr, "Failed line %d: %s\n", __LINE__, #expr); return 1; } } while (0)

int main(void)
{
    const uint32_t whole[] = { 0x80001000u, 9u };
    const uint32_t split[] = { 0x1000u, 4u, 0x1004u, 5u };
    const uint32_t overrun[] = { sizeof(ram) - 4u, 8u };
    const uint32_t empty[] = { 0u, 0u };
    memcpy(ram + 0x1000, "123456789", 9);
    CHECK(shinka_overlay_code_matches(whole, 1, 0xCBF43926u));
    CHECK(shinka_overlay_code_matches(split, 2, 0xCBF43926u));
    /* Simulate replacement without notifying any generation counter. */
    ram[0x1004] ^= 1;
    CHECK(!shinka_overlay_code_matches(whole, 1, 0xCBF43926u));
    ram[0x1004] ^= 1;
    CHECK(shinka_overlay_code_matches(whole, 1, 0xCBF43926u));
    CHECK(!shinka_overlay_code_matches(whole, 1, 0u));
    CHECK(!shinka_overlay_code_matches(overrun, 1, 0u));
    CHECK(!shinka_overlay_code_matches(empty, 1, 0u));
    CHECK(!shinka_overlay_code_matches(NULL, 1, 0u));
    CHECK(!shinka_overlay_code_matches(whole, 0, 0u));
    CHECK(!shinka_overlay_code_matches(whole, 4097, 0u));
    available = 0;
    CHECK(!shinka_overlay_code_matches(whole, 1, 0xCBF43926u));
    puts("Overlay guard regression checks passed.");
    return 0;
}
