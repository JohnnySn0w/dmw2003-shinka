# Menu and map groundwork — September 9, 2026

The native runtime displays the original status menu and Asuka map correctly.
The Wire Forest Entrance icon and location label were inspected in a copied
save. No teleport or in-game multiplier/encounter settings entry is implemented.

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
5. Add settings for independent normal/DV multipliers and random encounter rate,
   including zero random encounters while preserving scripted fights.

The inspected FastTravel reference package describes X on map icons and travel
on closing the menu, plus Square to switch server maps. Its documentation also
reports hangs from some post-game underwater/underground destinations. This
supports the interaction design but does not validate Shinka's transition hooks.
No replacement game module from that package has been installed or copied into
the repository. The selected-icon variable, transition entry point and visited
flags remain to be identified locally.
