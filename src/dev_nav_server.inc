/* Included in a generated copy of the pinned debug server. */
#include "dev_nav.h"
static void handle_shinka_nav(int id,const char* json) {
    char op[32];
    const char* error=NULL;
    int expected=json_get_int(json,"expected_mode",-1);
    if (!json_get_str(json,"op",op,sizeof(op))) { send_err(id,"Missing op");return; }
    if (!strcmp(op,"lab")) {
        ShinkaNavLab s;
        error=shinka_nav_lab(&s);
        if(error) { send_err(id,error);return; }
        send_fmt("{\"id\":%d,\"ok\":true,\"schema\":1,\"root\":%u,\"lifecycle\":%u,"
            "\"phase\":%u,\"slot\":%u,\"roster\":[%u,%u,%u],\"action_menu\":%u,"
            "\"action_phase\":%u,\"action\":%u}",id,s.root,s.lifecycle,s.phase,s.slot,
            s.roster[0],s.roster[1],s.roster[2],s.action_menu,s.action_phase,s.action);
        return;
    }
    if (!strcmp(op,"where")) {
        ShinkaNavState s;
        shinka_nav_state(&s);
        send_fmt("{\"id\":%d,\"ok\":true,\"schema\":1,\"mode\":%u,\"queued\":%u,"
            "\"story\":%u,\"stage\":%u,\"x\":%u,\"y\":%u,\"facing\":%u,"
            "\"encounters\":%u,\"countdown\":%u,\"quick_menu\":%u,\"quick_phase\":%u,\"quick_row\":%u}",
            id,s.mode,s.queued,s.story,s.stage,s.x,s.y,s.facing,s.encounters,s.countdown,s.quick_menu,
            s.quick_phase,s.quick_row);
        return;
    }
    if (!strcmp(op,"party")) {
        char result[2048];size_t used;
        unsigned i;
        used=(size_t)snprintf(result,sizeof(result),"{\"id\":%d,\"ok\":true,\"partners\":[",id);
        for(i=0;i<8;++i) {
            ShinkaNavPartner p;
            shinka_nav_partner(i,&p);
            used+=(size_t)snprintf(result+used,sizeof(result)-used,
                "%s{\"index\":%u,\"level\":%u,\"hp\":%u,\"max_hp\":%u,"
                "\"mp\":%u,\"max_mp\":%u,\"strength\":%u}",i?",":"",i,
                p.level,p.hp,p.max_hp,p.mp,p.max_mp,p.strength);
        }
        send_fmt("%s]}",result);return;
    }
    if (!strcmp(op,"warp")) error=shinka_nav_warp(json_get_int(json,"stage",-1),
        json_get_int(json,"x",-1),json_get_int(json,"y",-1),
        json_get_int(json,"facing",-1),expected);
    else if (!strcmp(op,"story")) error=shinka_nav_story(json_get_int(json,"value",-1),expected);
    /* The pinned flat JSON helper matches the first quoted key string; using
     * flag_id avoids colliding with the operation's own "flag" value. */
    else if (!strcmp(op,"flag")) error=shinka_nav_flag(json_get_int(json,"flag_id",-1),
        json_get_int(json,"value",-1),expected);
    else if (!strcmp(op,"encounters")) error=shinka_nav_encounters(json_get_int(json,"enabled",-1),expected);
    else if (!strcmp(op,"heal")) error=shinka_nav_heal(json_get_int(json,"index",-1),expected);
    else if (!strcmp(op,"power")) error=shinka_nav_power(json_get_int(json,"index",-1),
        json_get_int(json,"value",-1),expected);
    else error="Unknown Shinka navigation operation";
    if(error) send_err(id,error);else send_ok(id);
}
