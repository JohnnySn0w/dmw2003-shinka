# Menu and map groundwork — September 9, 2026

The native runtime displays the original status menu and Asuka map correctly.
The Wire Forest Entrance icon and location label were inspected in a copied
save. The [expanded field menu](field-menu.md) now provides normal/DV EXP settings
and [0–200% random encounter adjustment](encounters.md).
Map teleportation remains unimplemented.

The original `STSTATUS.PRO` is 100,936 bytes. A live status-menu RAM capture
matched the entire extracted module at `0x80082cb0`, resolving the placeholder
`0x80000000` in the initial reference metadata. Local captures remain ignored.

Next implementation work:

1. Trace the highlighted icon index and confirm-button handler.
2. Resolve icons to field destinations and safe entry coordinates/directions.
3. Queue the chosen destination, close the menu, then use the game's existing
   field-transition path to load the destination and its assets.
4. Enforce visited-location and story/server restrictions; test return travel,
   cutscenes, underwater/underground exits and post-game boundaries.

The inspected FastTravel reference package describes X on map icons and travel
on closing the menu, plus Square to switch server maps. Its documentation also
reports hangs from some post-game underwater/underground destinations. This
supports the interaction design but does not validate Shinka's transition hooks.
No replacement game module from that package has been installed or copied into
the repository. The selected-icon variable, transition entry point and visited
flags remain to be identified locally.

The map interaction uses a freely movable cursor that gravitates toward nearby
icons, disappears after snapping, and leaves that icon selected. Travel should
consume the game's selected icon after this snap behavior; the hit-test radius
and selected-icon variable still require tracing.

Evolution-tree access and directional hints are specified in [the evolution journal design](evolution-journal.md). The English DIGIVOLUTIONS entry now opens the full portable lab. Its chart adds anonymous nodes for nearby locked forms, with directional hints on X. See the evolution journal document for discovery rules, validation limits and field-return behavior.
