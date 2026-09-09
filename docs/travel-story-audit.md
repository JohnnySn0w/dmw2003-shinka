# Fast travel: story gates and walkthrough scope

Audited 2026-09-09 against the Shinka implementation at `8198337`.

The walkthroughs identify a manageable set of travel-sensitive events. The
useful policy is to shorten repeat journeys while preserving first entrances,
scripted exits, temporary closures and transport unlocks. A previously visited
area can become inaccessible later. Both departure and arrival need checks.

This is an implementation scope and test plan, not a completed campaign safety
certification. No runtime restrictions changed during this audit. The current
six-destination network still uses the broad story-byte range described in
[map travel](menu-map.md). That range does not prove the events below are safe.

## Evidence and version boundaries

- **Guide evidence** identifies event order and places to investigate. A guide
  telling the player to speak to somebody does not prove that conversation is a
  required flag. We must distinguish hints from actual prerequisites in the game.
- **Code evidence** below means a predicate was read in Shinka or the reference
  mod. A reference mod's workaround is a lead, not proof of the original game's
  intent or a verified Shinka fix.
- **Proposed policy** is our design inference. Each policy needs a matching
  original-game predicate and before/after testing before becoming an access rule.

The main-story sources are the authored walkthroughs by
[EmeraldPhoenix, v1.3](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/18310),
[Dark_Zero, v1.7](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/17652),
and [Divinesage, v1.3](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/17573).
They are indexed as **Digimon World 3**, so their event descriptions are leads
to verify in the English PAL `SLES_039.36` build. For postgame, use
[Funeralord's specifically PAL World 2003 guide, v1.13](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/70656).
Do not import US endgame assumptions into PAL postgame.

## Campaign checkpoints

The middle column contains brief guide facts; the last column contains proposed
travel behavior. IDs are audit identifiers, not the game's quest numbers.
Unless the code section below says otherwise, exact RAM predicates remain unmapped.

| ID | When / guide evidence | Proposed restriction and release condition |
| --- | --- | --- |
| T01 | Before the first badge: Seiryu's absent leader requires the MasterTyrannomon challenge. [Dark_Zero: Protocol Ruins–Seiryu](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/17652) | Outdoor revisits are candidates; avoid spawning inside leader rooms. Preserve the game's challenge and return sequence. |
| T02 | After the Seiryu badge: Teddy's announcement occurs on the Wind Prairie exit. Keith later intercepts the Asuka approach during the Blue Card search. [EmeraldPhoenix: chapter 3](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/18310) | Check **departure from Seiryu**, plus Asuka arrival. Keep the normal exit until its event completes; choose an approach before Keith's trigger until that encounter completes. Highest priority for the existing network. |
| T03 | First South Sector journey: the real Blue Card enables the gondola; Bulbmon interrupts the ride. [Dark_Zero: East Station](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/17652) | Unlock South arrivals only after the original journey finishes. Card possession alone should not substitute for completed transport. Station platforms need independent landing checks. |
| T04 | South route: recovering Sepikmon's mask yields the Smelly Herb that removes Zanbamon. [Dark_Zero: Tranquil Swamp–Phoenix Bay](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/17652) | Shorten the errands, retaining each interaction. Keep arrivals on the accessible side of Zanbamon until the removal event completes. A visited Jungle Grave screen does not prove both sides are accessible. |
| T05 | After Suzaku: Kail returns Junior to Asuka; Agumon disguises provide Admin Center entry. [Dark_Zero: Suzaku–Admin Centre](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/17652) | Preserve the forced return and disguise sequence. Do not add Admin interiors as ordinary destinations or allow departures during their scripted sequence. |
| T06 | Westward travel follows the Digi-Egg of Sincerity and underwater routes. [Dark_Zero: BIOS Swamp–West Sector](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/17652) | Require the actual transport capability and a naturally reached landing. Check that a surface destination has a usable return route; retain native water entry/exit handling. |
| T07 | Byakko's false leader leads into captivity and Numemon's escape. Dum Dum Factory subsequently uses a pursuit sequence before HiAndromon. [Dark_Zero: Byakko–Factory](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/17652) | Exclude prison, pursuit and boss interiors as sources and destinations initially. Add safe exterior exits only after proving they leave the sequence resumable. |
| T08 | Following Lucky Mouse's hideout events, Asuka's gates close. Datamon opens the sewer route after the Staff Pass errand. [EmeraldPhoenix: chapter 10](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/18310) | Keep Asuka arrival outside the closure. A bridge arrival may remain useful throughout the errand; do not teleport behind the gate. Reopen an interior destination only when its native access check permits it. |
| T09 | After liberation: Phoenix Bay has an earthquake scene; the Catacomb/Bug Maze route and Bulbmon precede the first Amaterasu arrival. [EmeraldPhoenix: chapter 11](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/18310) | Suzaku arrival must preserve the approach event. Cross-server travel stays unavailable until the normal crossing and arrival sequence finish. |
| T10 | First Amaterasu visit: Kenny supplies the Crony ID; city-chief encounters precede the Knowledge egg in Zhu Que UG Lake. [Divinesage: Amaterasu Server](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/17573) | Preserve Kenny and the original city gates. Treat each server as a distinct destination network. An Asuka visit must never unlock the corresponding Amaterasu field. |
| T11 | Return from Amaterasu: Digmon's Plug Cape route reaches the North Sector. [Divinesage: return to Asuka / North Sector](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/17573) | Unlock North arrivals after the transport unlock and actual first arrival. Preserve local dungeon progression; do not infer interior access from the city's map icon. |
| T12 | North dungeons lead to the Emergency Room and a 180-second underwater mission, followed by automatic return and the Destromon sequence. [Divinesage: Emergency Room](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/17573) | Block travel during the timed mission in both directions. Keep its transport and return owned by the original script. Resume only after normal field control returns. |
| T13 | Later Amaterasu: the Resistance/Lisa sequence opens Bai Hu; four chief ID passes permit passage past Knightmon into Amaterasu City. [Divinesage: Mirage Tower–Amaterasu City](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/17573) | Treat the desert approach, Bai Hu gate and Amaterasu gate separately. Arrive before a closed gate or decline travel; possessing an unrelated pass is insufficient. |
| T14 | After Destromon: Keith and Airdramon are part of the restoration sequence. Later, Asuka HQ and Kail's Central Park scene precede the final confrontation. [EmeraldPhoenix: chapter 18](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/18310) | Re-audit city exits and Central Park arrivals in both servers. Keep scripted departure/approach events; allow repeat errands once the relevant events finish. Do not extend the current story range wholesale. |
| T15 | Entering Gunslinger's portal is a point of no return. [EmeraldPhoenix: chapters 18–19](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/18310) | Keep all final-dungeon stages outside the travel source and destination sets. Lifting this is a separate sequence-changing feature. |
| T16 | PAL postgame relocates leaders and replaces the underground routes with substantially larger Circuit Boards. [Funeralord: introduction / Circuit Board maps](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/70656) | Build a separate, positively validated postgame network. Pre-ending visits cannot authorize removed routes. Test NPC services and every water/underground connection reachable from an arrival. |

Optional activities also need exit semantics. For example, leaving Kicking Forest
ends Veemon's hide-and-seek attempt. A future departure point there must invoke
equivalent cleanup or remain unavailable during the activity.
[Divinesage: Tree Boots sidequest](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/17573)
Card matches, tournaments and other minigames should remain excluded until their
normal exit behavior has been checked. This audit does not inventory every sidequest.

## Exact code leads

Shinka reads the story byte at `0x8004b370` and currently accepts `1..0x24`
(decimal 1–36). This is a scope cutoff, **not a decoded postgame boundary**.
Exact landing visitation comes from `0x8004b3c0 + (stage & 0xff) / 8`, using bit
`(stage & 0xff) % 8`. Neither value encodes the entire access policy.

The reference is Flawe's Fast Travel 2.0 as packaged in
[D-W-3-Recomp commit e7c2cd4](https://github.com/Xive080/D-W-3-Recomp/tree/e7c2cd48e1a15a93aeafe543f4e3bdc7b40a3243/source/flawe/FastTravel).
Its destination-adjustment routine begins at `0x8009ba84`, with related checks
at `0x8009ba0c`. Addresses use the `STSTATUS.PRO` load base `0x80082cb0`.
These are reference-mod predicates; they are **not implemented in Shinka** as
the conditional rules below.

| Reference predicate | Reference action | Interpretation / next check |
| --- | --- | --- |
| Destination `0x200`; story `6`; `(byte[0x8004b3e0] & 0x40) == 0` | Redirect to `0x202`, coordinates `(0x27e34, 0x12bcc)` | Asuka approach exception. Keith is a guide-based candidate; the bit's meaning and trigger position require original-script confirmation. |
| Destination `0x200`; story `20..23` | Redirect to `0x202`, `(0x2dda8, 0xf760)` | Strong candidate for the Asuka closure window. Shinka always uses this bridge landing, including outside these phases; that does not validate the earlier exception. |
| Destination `0x23e`; story `25`; `(byte[0x8004b3bf] & 2) == 0` | Redirect to `0x23b`, `(0x509c0, 0xdde0)` | Suzaku City to Phoenix Bay. The earthquake approach in T09 is a candidate explanation; confirm what sets the bit. |
| Destination `0x270`; story `< 37` | Redirect to `0x272`, `(0x17ec8, 0x1ac9a)` | Amaterasu City to its bridge. Inspect Knightmon's access test and the arrival's side of that gate. This does not identify story 37 as postgame. |
| Destination `0x2c1` or `0x2c3`; story `34..36` | Redirect to `0x2c0`, `(0x15ee2, 0x23a9a)` | Amaterasu Mobius Desert / Mirage Tower to Noise Desert. Investigate Resistance approach events. This is **not** a direct Bai Hu destination redirect. |

Stage identities were independently checked against the original stage-to-map-icon
table at `0x8009b5fc`: `0x200/0x202` share Asuka icon 20;
`0x23e` is Suzaku icon 42; `0x23b` is Phoenix Bay icon 46;
`0x270/0x272` share Amaterasu icon 20; and `0x2c0/0x2c1/0x2c3` map
to Amaterasu icons 35/40/39. The table identifies map groups, not every interior
or the correct side of an event trigger.

Reproducibility: original module SHA-256
`892300687ec6a8d69c7c2b6c6111adffb5df3beee301e9ef919ee78c02f24e8a`;
reference module SHA-256
`aab111677441e592c3f2f391c21c23e88ac57a63b2258a499681ef30634c2696`.
The binaries and disassembly remain local; only findings are recorded here.

The reference's [walkthrough documentation](https://github.com/Xive080/D-W-3-Recomp/blob/e7c2cd48e1a15a93aeafe543f4e3bdc7b40a3243/source/flawe/Walkthrough/README.md)
credits markisha64's quest-system research and explicitly limits that feature to
the main story. Its quest selector is another investigation lead, not a substitute
for validating side activities or PAL postgame.

The [reference travel documentation](https://github.com/Xive080/D-W-3-Recomp/blob/e7c2cd48e1a15a93aeafe543f4e3bdc7b40a3243/source/flawe/FastTravel/README.md)
reports missing NPCs and underwater/underground hangs when its postgame travel
leaves the supported world. These are the reference author's reported results,
not crashes reproduced in Shinka. They support retaining a postgame allowlist.

## Priorities for the existing network

| Current field | First check before broader campaign claims |
| --- | --- |
| Seiryu City `0x22e` | T02 departure: can teleport bypass the exit event, and does returning recover it? Compare natural and teleported paths immediately after the badge. |
| Asuka bridge `0x202` | Compare both reference coordinates during the story-6 exception; then test closure and reopening. Verify movement reaches the required trigger instead of landing beyond it. |
| Asuka Main Lobby `0x200` (source only) | Audit departures during forced-return, disguise and liberation sequences. Being a supported source must not allow escape from unfinished scripts. |
| Central Park `0x21d` | Establish event-free departure and arrival positions for each allowed phase. T14 is also a prerequisite before admitting later phases or the other server. |
| Wire Forest Entrance `0x21e` and Wire Forest `0x222` | Lower-priority candidates for broad repeat travel; no special closure was identified in the reviewed passages. This is an evidence gap, not proof that none exists. |
| Pelche Oasis `0x249` | Verify T06 transport access and ordinary return routes. Keep T07 interiors excluded; a nearby safe outdoor point does not make the whole map group safe. |

## Implementation and validation plan

1. **Resolve T02 and T08 first.** Follow original event scripts and observe normal
   completion around the Seiryu exit, Keith approach and Asuka closure. Name a
   flag only after identifying its readers/writers or observing its transition
   with a matching script. Do not guess numeric story values from chapter order.
2. **Separate departure from arrival policy.** Evaluate current field, server,
   story, event state, transport capability and exact landing visit. Return one
   of: travel to the normal landing, travel to a validated approach, or unavailable.
   Keep decisions read-only with respect to progression.
3. **Expand surface hubs in campaign order.** South after T03/T04, West after
   T06/T07, then the server and North unlocks. Validate the five reference
   exceptions individually. Keep unvalidated interiors excluded.
4. **Handle later phases and postgame separately.** Resolve T12–T16 before raising
   the global cutoff. Use a distinct postgame field/connection allowlist and
   confirm the actual PAL mode predicate.

For every restriction, retain private checkpoints immediately before the event,
after its trigger, after completion, and after the next ordinary transition.
Exercise natural travel and teleport from equivalent starting states. Check the
next required event, NPC availability, walking out, returning, and an ordinary
save/reload. Compare progression with the natural route; unchanged flags during
the teleport alone are insufficient. Never manufacture completion by setting a
quest bit during the test.

Once predicates are implemented, add native policy tests for both sides of each
boundary, wrong-server destinations, stale visits, alternate landings and timed
departures. Re-evaluate the same policy on selection and at the existing deferred
cut, including subflags that can change without the story byte changing. Retain
cancel and pending-savestate coverage. The existing direct transition can be
reused; safe travel does not require reopening the root menu.

Player-facing reasons should describe the action available, for example
**Visit this area first**, **Travel to city entrance**, or **Travel unavailable
during this event**. Keep internal story numbers and future plot details out of
the map UI.
