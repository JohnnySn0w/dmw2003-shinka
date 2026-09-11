#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "cdrom_irq.h"
#include "event_ring.h"

static uint64_t psx_cycle_count, cdrom_irq_present_due, pending_present_due;
static uint8_t irq_flag, irq_enable;
static int cdrom_intc_request_latched, reading, read_delay, warm_blocked;
static uint32_t cdrom_irq_generation, cdrom_intc_latched_generation, i_stat;
static struct { int pending; uint64_t due_cyc; } pending;
#define CDIRQ_DATA_READY 1
typedef struct { uint64_t cycle; uint32_t bit, detail; } Edge;
static Edge edges[32];
static unsigned edge_count;
static int warm_route_consumer_blocked(void) { return warm_blocked; }
static void psx_irq_raise(uint32_t bit, uint32_t detail) {
    if (edge_count < 32) edges[edge_count] = (Edge){psx_cycle_count, bit, detail};
    ++edge_count; i_stat |= 1u << bit;
}
static void trace_cdrom(char kind, uint8_t reg, uint32_t value, int size) {
    (void)kind; (void)reg; (void)value; (void)size;
}
void event_ring_record(uint16_t kind, uint8_t detail) { (void)kind; (void)detail; }
void event_ring_record_aux(uint16_t kind, uint8_t detail, uint32_t aux) { (void)kind; (void)detail; (void)aux; }
static void cd_timing_note_intc(void) {}
#include "cd_deadline_fixture.inc"
#define CHECK(e) do { if (!(e)) { fprintf(stderr,"CD deadline failed at %d: %s\n",__LINE__,#e); return 1; } } while(0)

static void reset(int enabled) {
    psx_cycle_count=1000; cdrom_irq_present_due=pending_present_due=0;
    irq_flag=0; irq_enable=7; cdrom_intc_request_latched=0;
    reading=read_delay=warm_blocked=0; memset(&pending,0,sizeof(pending));
    cdrom_irq_generation=cdrom_intc_latched_generation=i_stat=edge_count=0;
    shinka_cd_deadline_enabled=enabled; memset(edges,0,sizeof(edges));
}

int main(void) {
    Edge baseline[32]; unsigned baseline_count=0;
    for (int enabled=0; enabled<=1; ++enabled) {
        reset(enabled);
        CHECK(cdrom_cycles_to_irq(UINT32_MAX)==UINT32_MAX);
        set_irq(1);
        CHECK(cdrom_cycles_to_irq(UINT32_MAX)==CDROM_IRQ_PRESENT_DELAY);
        CHECK(cdrom_cycles_to_irq(0)==UINT32_MAX);
        psx_cycle_count=cdrom_irq_present_due-1;
        present_cdrom_irq(); CHECK(edge_count==0);
        CHECK(cdrom_cycles_to_irq(UINT32_MAX)==1);
        ++psx_cycle_count; present_cdrom_irq();
        CHECK(edge_count==1 && (i_stat&4));
        CHECK(cdrom_cycles_to_irq(UINT32_MAX)==(enabled?UINT32_MAX:0));
        /* INTC acknowledgement alone must not re-present the current CD INT. */
        i_stat=0;
        for (int i=0;i<10000;++i) { ++psx_cycle_count; present_cdrom_irq(); }
        CHECK(edge_count==1 && i_stat==0);
        /* A new CD response re-arms delivery at its original delayed cycle. */
        set_irq(3); CHECK(!cdrom_intc_request_latched);
        CHECK(cdrom_cycles_to_irq(UINT32_MAX)==CDROM_IRQ_PRESENT_DELAY);
        psx_cycle_count=cdrom_irq_present_due; present_cdrom_irq();
        CHECK(edge_count==2 && cdrom_intc_latched_generation==2);
        if (!enabled) { memcpy(baseline,edges,sizeof(edges)); baseline_count=edge_count; }
        else CHECK(edge_count==baseline_count && !memcmp(baseline,edges,sizeof(edges)));
    }
    reset(1); set_irq(1); psx_cycle_count=cdrom_irq_present_due; present_cdrom_irq();
    reading=1; read_delay=400;
    CHECK(cdrom_cycles_to_irq(UINT32_MAX)==400);
    pending.pending=1; pending.due_cyc=psx_cycle_count+200;
    CHECK(cdrom_cycles_to_irq(UINT32_MAX)==200);
    pending_present_due=psx_cycle_count+100;
    CHECK(cdrom_cycles_to_irq(UINT32_MAX)==100);
    pending_present_due=0; pending.due_cyc=psx_cycle_count;
    CHECK(cdrom_cycles_to_irq(UINT32_MAX)==400); /* occupied response FIFO */
    irq_flag=0; cdrom_intc_request_latched=0;
    CHECK(cdrom_cycles_to_irq(UINT32_MAX)==0); /* pending response now released */
    pending.pending=0; warm_blocked=1;
    CHECK(cdrom_cycles_to_irq(UINT32_MAX)==UINT32_MAX);
    warm_blocked=0; CHECK(cdrom_cycles_to_irq(UINT32_MAX)==400);
    /* Controller mask and encoded reasons retain all original combinations. */
    for(unsigned mask=0;mask<8;++mask) for(unsigned reason=1;reason<=5;++reason) {
        reset(1); irq_enable=(uint8_t)mask; set_irq(reason);
        int allowed=cdrom_irq_mask_matches_reason(irq_enable,irq_flag);
        CHECK(cdrom_cycles_to_irq(UINT32_MAX)==(allowed?CDROM_IRQ_PRESENT_DELAY:UINT32_MAX));
        psx_cycle_count=cdrom_irq_present_due; present_cdrom_irq();
        CHECK(edge_count==(unsigned)allowed);
        CHECK(cdrom_cycles_to_irq(UINT32_MAX)==UINT32_MAX);
        /* Enable after a masked deadline; the previously undelivered edge is due. */
        if (!allowed) { irq_enable=7; CHECK(cdrom_cycles_to_irq(UINT32_MAX)==0); present_cdrom_irq(); CHECK(edge_count==1); }
    }
    puts("CD deadlines retain delivery/re-arm edge timing, masks, sector and pending-response deadlines.");
    return 0;
}
