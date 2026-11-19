#include <stdio.h>
#include <stdlib.h>
#include "settings_buttons.h"
static int active;
int shinka_menu_settings_active(void) { return active; }
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"line %d: %s\n",__LINE__,#c); exit(1); } } while(0)
int main(void) {
    CHECK(shinka_settings_button_direction(0x1200,0x3a17,0x226)==-1);
    active=1;
    CHECK(shinka_settings_button_direction(0x1200,0x3a17,0x226)==0);
    CHECK(shinka_settings_button_direction(0x1208,0x3a17,0x226)==1);
    CHECK(shinka_settings_button_direction(0x1208,0x3817,0x226)==-1);
    CHECK(shinka_settings_button_direction(0x1208,0x3a17,0x225)==-1);
    CHECK(shinka_settings_button_direction(0x1209,0x3a17,0x226)==-1);
    uint16_t packed[36], palette[16], left[144], right[144];
    for(int i=0;i<16;++i) palette[i]=(uint16_t)(i*0x421);
    for(int i=0;i<36;++i) packed[i]=0x1111;
    /* Synthetic transparent corners, edge shading and coloured symbol. */
    packed[0]=0x5430; packed[2*3+1]=0x9988; packed[5*3+1]=0x9988;
    shinka_settings_button_pixels(packed,palette,0,left);
    shinka_settings_button_pixels(packed,palette,1,right);
    CHECK(left[0]==0 && left[1]==palette[3] && left[2]==palette[4] && left[3]==palette[5]);
    CHECK(right[0]==0 && right[1]==palette[3]);
    for(int x=4;x<8;++x) CHECK(left[2*12+x]==palette[1] && right[2*12+x]==palette[1]);
    CHECK(left[5*12+4]==palette[2] && right[5*12+7]==palette[2]);
    CHECK(left[5*12+3]==palette[1] && right[5*12+8]==palette[1]);
    for(int y=1;y<12;++y) for(int x=0;x<12;++x)
        CHECK(left[y*12+x]==right[y*12+11-x]);
    return 0;
}
