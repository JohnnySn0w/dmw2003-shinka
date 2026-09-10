# Fast travel: story gates and walkthrough scope

Walkthrough scope audited 2026-09-09 against `8198337`; the first runtime guards
were subsequently traced and implemented as described below.

The walkthroughs identify a manageable set of travel-sensitive events. The
useful policy is to shorten repeat journeys while preserving first entrances,
scripted exits, temporary closures and transport unlocks. A previously visited
area can become inaccessible later. Both departure and arrival need checks.

This is an implementation scope and test plan, not a completed campaign safety
certification. The ten-destination network now guards Seiryu's pending departure
scene, adjusts Asuka's early arrival, gates three South Sector stops behind the
completed first arrival, and admits Phoenix Bay only after its exact surface field
has been visited. It retains the broad story range
described in [map travel](menu-map.md). That range does not prove the remaining
events below are safe.

## Evidence and version boundaries

- **Guide evidence** identifies event order and places to investigate. A guide
  telling the player to speak to somebody does not prove that conversation is a
  required flag. We must distinguish hints from actual prerequisites in the game.
- **Code evidence** identifies whether a predicate comes from original field
  scripts, Shinka, or the reference mod. A reference workaround is a lead, not
  proof of the original game's intent or a verified Shinka fix.
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

Shinka reads the 32-bit story word at `0x8004b370` and accepts `1..0x24`
(decimal 1–36). This is a scope cutoff, **not a decoded postgame boundary**.
Exact landing visitation comes from `0x8004b3c0 + (stage & 0xff) / 8`, using bit
`(stage & 0xff) % 8`. Neither value encodes the entire access policy.

The reference is Flawe's Fast Travel 2.0 as packaged in
[D-W-3-Recomp commit e7c2cd4](https://github.com/Xive080/D-W-3-Recomp/tree/e7c2cd48e1a15a93aeafe543f4e3bdc7b40a3243/source/flawe/FastTravel).
Its destination-adjustment routine begins at `0x8009ba84`, with related checks
at `0x8009ba0c`. Addresses use the `STSTATUS.PRO` load base `0x80082cb0`.
These are reference-mod predicates. The first was subsequently verified against
the original bridge script and implemented; the other conditional redirects have
not been added. Shinka already uses an outside bridge landing during lockdown.

| Reference predicate | Reference action | Interpretation / next check |
| --- | --- | --- |
| Destination `0x200`; story `6`; `(byte[0x8004b3e0] & 0x40) == 0` | Redirect to `0x202`, coordinates `(0x27e34, 0x12bcc)` | Keith's early encounter. Original-script confirmation and the implemented arrival are documented below. |
| Destination `0x200`; story `20..23` | Redirect to `0x202`, `(0x2dda8, 0xf760)` | Candidate closure window. Shinka keeps this bridge landing during those phases, leaving access to the original gate script. |
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

## Implemented original-script guards

The story counter is a **32-bit word**, not the low byte used by the initial
prototype. Original field modules read and write it with word instructions.
Selection and both deferred transition paths now use the full value and resolve
the same policy from current RAM. A subflag change cannot leave a stale landing
or bypass a new departure restriction. No progression flags are written by travel.

| Original evidence (file offsets) | Implemented behavior |
| --- | --- |
| `WSTAG420.PRO`, badge routine at `0x13c..0x190`, writes story `5`. `WSTAG395.PRO` at `0x38..0x64` launches event `0x50` only for story `5` and flag `0x4011` clear. Its completion callback at `0x134..0x15c` sets that flag. | Seiryu (`0x22e`) departures show **Use the city exit** while that predicate holds. Travel resumes when the conversation finishes, even though story remains `5`. Travel **into** Seiryu remains allowed. |
| `WSTAG205.PRO` at `0x334..0x388` tests story `6`, encounter-start flag `0x4006` set, and completion flag `0x4016` clear before launching follow-up event `0x65`. The callback at `0x410..0x458` sets the start flag; `0x45c..0x484` sets completion. | Asuka (`0x202`) uses `(0x27e34, 0x12bcc)` while story is `6` and completion is clear. Otherwise it uses `(0x2dda8, 0xf760)`. The map labels this **X: City entrance**. The original encounter and gate scripts retain control. |

The resident flag reader `0x800163b0` maps class `0x40` to bitset `0x8004b3de`.
Its low flag index selects the bit: `0x4011` is byte `0x8004b3e0`, mask `2`;
`0x4016` is the same byte, mask `0x40`. The setter is `0x800165ac`.
The original global function table at `0x80048abc` contains the setter at `+0xc`
and reader at `+0x10`, matching the indirect calls in these modules.

The original `FIELDSTG.PRO` stage table at `0x8009a884` independently resolves
`0x202` to `WSTAG205`, `0x229` (Wind Prairie) to `WSTAG395`, and `0x22e`
(Seiryu) to `WSTAG420`. `WSTAG410` belongs to East Station (`0x22c`): its
story `5 -> 6` write is **not** Teddy's completion. Waiting for story `6`
would unnecessarily keep Seiryu travel locked after the announcement.

The annotated instruction words were compared with modules extracted from the
owner's PAL disc. Reproducible SHA-256 fingerprints:

| Module | SHA-256 |
| --- | --- |
| `WSTAG205.PRO` | `04947dd9329abaf269a224daedfc39eb61bf0e9c8b6bdf007477545c1abd4a4c` |
| `WSTAG395.PRO` | `c39fddb86ea006d3b6feded40ca7fb6e7a54cd184db0e6537690ef907851c87a` |
| `WSTAG420.PRO` | `613cf3d7c5a39bfbf38fe9c6ced49dd33406ba3e7f3a49537448a20002a5a0b4` |

Native regression covers all exposed Seiryu departures, completion within story
`5`, recovery travel into Seiryu, neighboring story phases, unrelated flag bits,
Asuka's two landings, lockdown phase boundaries, high story-word rejection, and
subflag changes between selection and commit. Both the direct cut and old
pending-menu savestates recheck the policy. The test's write allowlist rejects
progression writes.

Live checks use an isolated copy of an advanced save, with the story and relevant
event flags reset to construct explicit **test fixtures**. They are not naturally
earned early-game checkpoints. In the Seiryu fixture, confirming the blocked map
selection leaves the map open. Walking through the normal exit starts Teddy's
dialogue; completing it normally sets `0x4011` while story stays `5`. Walking back
into Seiryu then permits travel to Central Park. The trip leaves the checked
progression bytes unchanged. No completion flag is forced during this sequence.
The Asuka fixture lands at the alternate coordinates and immediately starts the
original Keith dialogue and battle. Winning and finishing the follow-up dialogue
sets `0x4016` through the original script, with story still `6`. See
[map travel validation](menu-map.md) for subsequent runtime checks and remaining
coverage. These event checks do not substitute for a full campaign run through
the badge, Blue Card errands, lockdown and reopening.

## First South Sector stops

South Station (`0x232`), Bulk Bridge (`0x234`) and Tranquil Swamp (`0x237`) are
available after the first South arrival completes. Bulk Swamp (`0x233`) is also
a departure source. The same policy runs on map selection, direct commit and
legacy pending-state completion:

1. Require story at least `7`, within the existing overall `1..36` limit.
2. Require the recorded South Station visit, `0x8004b3c6 & 4`.
3. Require the exact destination's visit; Bulk Swamp's visit does not substitute
   for Bulk Bridge even though they share map icon 43.

This follows the original South Station module `WSTAG440.PRO`: offsets
`0x40..0x5c` launch arrival event `0x98` when story is `6`; the completion callback
at `0xcc..0xd8` writes `7`. The event also moves the party to Bulk Swamp. The
first arrival must complete before departures or arrivals involving these four
fields. Possession of the Blue Card is not treated as completion.

The original field-stage table independently maps `0x232/0x233/0x234/0x237` to
`WSTAG440/445/450/465`. The original status table maps them to icons `32/43/43/44`.
Landing leads came from Flawe's reference table, then were checked in Shinka:

| Arrival | Coordinates | Reference table address |
| --- | --- | --- |
| South Station | `(0x15ade, 0x111cd)` | `0x8009bf9c` |
| Bulk Bridge | `(0x3dc56, 0x1f77c)` | `0x8009bfc4` |
| Tranquil Swamp | `(0x2d205, 0x106a6)` | `0x8009c000` |

Annotated instruction words matched the owner's original modules. SHA-256:

| Module | SHA-256 |
| --- | --- |
| `WSTAG440.PRO` | `65fba20ff6686a675e69255ba60e037bf987e3220f621308f4f866a29047118f` |
| `WSTAG445.PRO` | `a26ef28702d8358fcaf0114303d39b7ab61618a6a6e0580c9f681d5e0e307c38` |
| `WSTAG450.PRO` | `725061b3c988ab745c63e8e09f25995f9404f1c5ee7d43e7128be6eedc6f6e5e` |
| `WSTAG465.PRO` | `1915774a80702694c9f5dd269ceb624c2522ab794a51d6a61686850cad8f8a5d` |

[Live validation](menu-map.md) covers all three first-arrival landings, station transport,
ordinary bridge/swamp transitions and a controlled `6 -> 7` arrival fixture.
The first gondola battle and preceding errands still need a naturally earned
checkpoint; the synthetic setup must not be mistaken for a full quest replay.

This extends T03 coverage. It does not add travel past Zanbamon or into the
Suzaku forced-return sequence. Jungle Grave remains excluded because its first
entry owns the Zanbamon encounter and returns the party through the native event.
Phoenix Bay is now a validated surface landing at stage `0x23b`, icon `46`, gated
by its exact visit bit; its landing was checked using developer warps from an
isolated story-7 profile. Those warps bypass the player-map policy. The gondola,
inn/shaman interiors and Suzaku remain outside the network.
T04/T05 and the later Phoenix Bay approach still need their own predicates and
live event checks before broader campaign claims. The pre-Zanbamon errands and
ordinary route are described in [Dark_Zero's walkthrough](https://gamefaqs.gamespot.com/ps/562323-digimon-world-3/faqs/17652).

## Phoenix Bay earthquake and Jungle Grave follow-up

The original Phoenix Bay module `WSTAG485.PRO` contains two conditions at
offsets `0x172c` and `0x1730`: `(0x6019, 1)` and `(0x1c51, 0)` as pairs of
little-endian halfwords. These mean **story exactly 25** and **flag 0x1c51 clear**.
`FIELDSTG.PRO` offsets `0x56d4..0x5738` evaluate both pairs through resident
function pointer `0x80048acc` (`0x800163b0`), rejecting either false condition.
The class-0x60 reader calls `0x80015ec8`, which compares the story word at
`0x8004b370` for equality (or inequality when its second argument is zero).

The record requests event `0x5fa`. Its completion callback at module offset
`0xa8..0xd0` sets flag `0x1c51` through pointer `0x80048ac8` (`0x800165ac`).
The resident class-0x1c reader/writer use base `0x8004b3b5`; this flag is byte
`0x8004b3bf`, mask `2`. This is distinct from the class-0x40 quest-bit storage.
The pointer values and storage operands were checked against the original EXE.
All 131 annotated code words in WSTAG485 and all 76 annotated words in the
reviewed FIELDSTG predicate/event-dispatch range matched the owner's files.

In an isolated story-25 fixture with that bit cleared, developer arrival at
`(0x509c0, 0xdde0)` produced the earthquake and Junior's **Tremors!** dialogue.
Finishing the dialogue naturally changed the byte from `0x09` to `0x0b`, with
story remaining 25. Repeating the setup at the usual south-side landing
`(0x437f2, 0x29469)` did not start the scene. The northern coordinate was a
reference-table investigation lead; these tests establish its behavior in Shinka.

Player-map travel now chooses the northern approach while that exact predicate
holds, and the ordinary landing otherwise. Selection, deferred cut and legacy
pending-savestate paths share the same calculation. Travel never sets the
completion flag. Native tests cover stories 24/25/26, both flag states, and
flag changes in either direction while a trip is pending.

The rebuilt runtime was also checked through the actual map: directional input
snapped to Phoenix Bay, its **X: Travel** prompt appeared, and Cross queued the
northern arrival and native event. Dialogue completion again set the bit
naturally. After a developer warp back to Central Park, a second actual map trip
reached the ordinary south bridge with the flag still set and no earthquake
replay. This was a controlled fixture built from a copied checkpoint, not a
replay of the preceding liberation quests. Suzaku remains excluded, and this
does not certify its forced-return sequence or every later South Sector event.
Local captures are under ignored `output/south-event-audit/`.

Jungle Grave's original `WSTAG480.PRO` confirms an entry condition at
`0x3f0..0x424`: story 7 plus flag `0x4000` set starts event `0xab`.
Its completion callback at `0x4f8..0x504` writes story 8. The field configuration
at `0x650..0x67c` selects different tables for story below 10, 10 through 23,
and 24 onward. That is evidence of multiple field phases, not proof that
Zanbamon can safely be bypassed at story 10. The item-dependent removal and
later encounter still need their own natural-route checks; Jungle Grave remains
excluded. All 417 annotated code words matched the original module.

Additional original module SHA-256 values:

| Module | SHA-256 |
| --- | --- |
| `WSTAG480.PRO` | `c18172ad722bac069ec366f2b2e4e753ef8b7be6adfda27d0cd12fafa007c51e` |
| `WSTAG485.PRO` | `7c08907352abb4ce92d19a14cc235a5e90f4aa03b47e8cbcea23bce020c63ca6` |
| `WSTAG500.PRO` | `c3b155360bc56eb12dadf5eb2ee5ee905e7f4774e61067985a1fb5a892386ecc` |

WSTAG500's 138 annotated code words also matched; this comparison alone is not
a Suzaku event audit.

### Suzaku condition records: partial audit

The new read-only `tools/field_conditions.py` reproduces these predicates from
the owned module at explicit, traced offsets:

| WSTAG500 offset | Conditions | Action |
| --- | --- | --- |
| `0x1c60` | Story exactly 10; flag `0x400a` clear | Start event `0xfa` |
| `0x1c78` | Story exactly 11; second condition unused | Start event `0x10e` |

The event table at `0x1cd8` associates `0xfa` with script `0x800a6004`
(module offset `0x224`) and callback `0x800a5e84` (offset `0xa4`). The callback
sets **both** `0x400a` and `0x1a32` through the resident setter. The former is
byte `0x8004b3df`, mask `4`; the tool deliberately leaves class-0x1a unresolved
until its decoding is added with independent checks.

The preceding event-table entry at `0x1cc4` associates `0x10e` with script
`0x800a6180` (offset `0x3a0`) and no completion callback. Absence of a callback
does not imply absence of progression writes: those can live in scene bytecode.
Do not use the story-10 callback as the completion test for the story-11 event.

A controlled story-11 developer warp to the reference Suzaku landing loaded the
field, but did not establish the forced-return trigger or its completion.
Walking and talking during this attempt reached **Tamer Alice**, not a verified
Kail return scene. Early visual identification of Kail was incorrect. No travel
permission or progression-completion claim follows from this attempt.

Likewise, a story-9 Jungle Grave fixture loaded successfully, but did not replay
the Smelly Herb interaction. The story-specific NPC condition lists at
`0x1184..0x11a0` distinguish stories 7, 8, 9 and 10; they do not alone prove
removal completion or item consumption. Both Jungle Grave and Suzaku stay
excluded. Next checks are the actual event-entry geometry/native entry path,
the item-dependent removal interaction, and each scene's downstream transition.

## Priorities for the existing network

| Current field | First check before broader campaign claims |
| --- | --- |
| Seiryu City `0x22e` | T02 guard and native announcement release verified in a controlled fixture above. Retain a naturally earned badge checkpoint for full campaign regression. |
| Asuka bridge `0x202` | Story-6 approach starts the original encounter. Complete the closure/reopening campaign regression; synthetic boundary tests alone do not certify all gate events. |
| South Station / Bulk Swamp / Bulk Bridge / Tranquil Swamp | First-arrival policy is implemented. Extend naturally earned checkpoints and later NPC-phase coverage before claiming campaign-wide safety. |
| Asuka Main Lobby `0x200` (source only) | Audit departures during forced-return, disguise and liberation sequences. Being a supported source must not allow escape from unfinished scripts. |
| Central Park `0x21d` | Establish event-free departure and arrival positions for each allowed phase. T14 is also a prerequisite before admitting later phases or the other server. |
| Wire Forest Entrance `0x21e` and Wire Forest `0x222` | Lower-priority candidates for broad repeat travel; no special closure was identified in the reviewed passages. This is an evidence gap, not proof that none exists. |
| Pelche Oasis `0x249` | Verify T06 transport access and ordinary return routes. Keep T07 interiors excluded; a nearby safe outdoor point does not make the whole map group safe. |

## Implementation and validation plan

1. **Finish T02 and T08 campaign coverage.** The first rules above are implemented.
   Follow original event scripts and observe normal
   completion around the Seiryu exit, Keith approach and Asuka closure. Name a
   flag only after identifying its readers/writers or observing its transition
   with a matching script. Do not guess numeric story values from chapter order.
2. **Extend the shared departure and arrival policy.** Evaluate current field, server,
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

For each additional predicate, add native policy tests for both sides of each
boundary, wrong-server destinations, stale visits, alternate landings and timed
departures. Re-evaluate the same policy on selection and at the existing deferred
cut, including subflags that can change without the story word changing. Retain
cancel and pending-savestate coverage. The existing direct transition can be
reused; safe travel does not require reopening the root menu.

Player-facing reasons should describe the action available, for example
**Visit this area first**, **Travel to city entrance**, or **Travel unavailable
during this event**. Keep internal story numbers and future plot details out of
the map UI.
