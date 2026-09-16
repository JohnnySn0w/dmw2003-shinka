# Controller compatibility

Decision: use the existing SDL3 gamepad layer as the default native Windows input path. Steam Input remains an optional compatibility route. The final build should support any Windows-accessible controller with enough usable controls, through automatic recognition or user mapping; that is an acceptance target, not a claim about the current prototype.

## Default controls

These are logical mappings; saved `input.ini` / `keybinds.ini` choices can override
them. A/B/X/Y below use the runtime's default gamepad labels, which may differ
from the letters printed on a particular controller.

| PlayStation input | Keyboard | Default gamepad control |
| --- | --- | --- |
| D-pad | Arrow keys | D-pad / mapped left stick |
| Cross (confirm) | X | A |
| Circle | S | B |
| Square | Z | X |
| Triangle (back) | A | Y |
| Start | Enter | Start |
| Select | Right Shift | Select / Back |
| L1 / R1 | Q / W | Left / right shoulder |
| L2 / R2 | E / R | Left / right trigger |

**Tab** is the host's hold-to-speedup key. At language selection, use **Start**
to confirm. In the evolution chart, **L1/R1** change pages and **Cross** opens
or closes a locked-form hint. Instructions saying “X” mean PlayStation Cross,
not the gamepad's X-labeled face button.

## Existing foundation

The pinned runtime already reads SDL gamepads, supports configurable logical bindings and per-GUID overrides, maps sticks into digital movement, and forwards emulated rumble. It also has device connection event handling and GUID selection with a first-available fallback. These are source-audited capabilities; physical-device compatibility and reconnect behavior still need testing in Shinka.

`build-windows/Release/input.ini` contains gamepad bindings; `keybinds.ini` contains keyboard bindings. They are created by the runtime and are separate from `game.toml`. SDL hardware mappings translate device buttons/axes to logical controls; `input.ini` translates those controls to PlayStation buttons. The final settings screen must expose both recovery from unknown hardware and ordinary rebinding without requiring file editing.

`game.toml` explicitly sets `[controller] p1_device = "auto"` so the build without
the launcher selects the first available SDL gamepad. Keyboard bindings stay live
alongside it, and connecting a recognized controller after startup follows the
same selection path. Without this setting, the pinned frontend defaults to
keyboard-only routing even when `input.ini` enables controllers. A saved
`build-windows/Release/settings.toml` controller selection takes precedence.

SDL supports many controllers through its built-in database and accepts custom mappings. See the [SDL gamepad overview](https://wiki.libsdl.org/SDL3/CategoryGamepad) and [mapping-file hint](https://wiki.libsdl.org/SDL3/SDL_HINT_GAMECONTROLLERCONFIG_FILE).

For a controller requiring an SDL mapping file:

```powershell
./tools/launch_windows.ps1 -DiscCue 'PATH\TO\game.cue' -ControllerMappings 'PATH\TO\gamecontrollerdb.txt'
```

The launcher resolves the file and supplies it to SDL before initialization, restoring the caller's environment afterward. Without this option, existing SDL environment settings remain untouched. The pinned SDL source contains this mapping-file path; actual unknown-controller behavior remains a hardware test.

## Trigger shortcuts

- **L2 / LT:** toggle 4:3 ↔ 16:9 for the current supported scene. Battles update
  the Battle preference; fields, supported menus and the map update Field.
  The choice persists and is reflected in SETTINGS. Unsupported scenes report
  that the shortcut is unavailable instead of changing a hidden preference.
- **R2 / RT:** toggle speedup on/off using the existing manual speed limit
  (4× by default). Tab remains hold-to-speedup; holding Tab still accelerates
  when the trigger toggle is off.

These use the mapped PlayStation inputs, so the default keyboard equivalents
are **E** and **R**. One press causes one change; holding does not repeat.
They operate while the game window has focus. Focus loss and savestate/host-menu
resume clear toggled speedup and require released triggers before rearming.
Speedup is session-only. Shortcuts are disabled for headless/replay/netplay
contexts. Native trigger input is still passed to the game; this does not
establish that every original scene leaves those buttons unused.

The 2026-09-15 live map check exercised mapped pad input through the local
diagnostic sampler: L2 switched both directions and R2 changed measured guest
cadence from approximately 50 to 135 frames/second and back on the test laptop.
The 4× speed limit is a ceiling, not a guaranteed rate. The native shortcut
regression covers long holds, simultaneous triggers, independent release,
disabled contexts and reset while held. The user subsequently reported that
the aspect-ratio and speedup trigger shortcuts worked. This is a user playtest
confirmation, not a full device/reconnection test matrix.

## Steam Input path

The intended optional path is to launch the executable through Steam with a gamepad layout and have SDL read the resulting gamepad. Keep the game configuration/disc arguments from the launch script when configuring a non-Steam shortcut. Steam launch behavior is not yet validated or packaged. Do not force-disable native backends globally: device selection must distinguish the physical device from a Steam virtual device and avoid duplicate input.

## Required before release

- Native Xbox/XInput, PlayStation, Switch-style, and generic USB devices; Bluetooth and wired connections where supported by the hardware.
- Steam Input on and off, including duplicate-device detection and predictable active-device selection.
- Plug in after startup, unplug while holding a direction, reconnect, change devices, and resume after focus loss; no stuck buttons.
- Complete rebinding, deadzone adjustment, profile persistence, and a visible input-test screen. Unknown devices need a mapping wizard; inaccessible hardware may still require a Windows driver or adapter.
- D-pad and left-stick movement, every PS1 button, triggers, simultaneous presses, and rumble where the controller supports it. Keep keyboard recovery available.
- Verify language confirmation with Start, menus, exploration, and battle controls against actual game behavior. Test digital-pad defaults before enabling analog emulation.

The user confirmed D-pad and A-button input on an **8BitDo Ultimate 2C Wireless
over Bluetooth** after the runtime opened the device. This verifies that device
and connection for basic input; the full physical-controller matrix has not
passed. Debug-server injected presses validate game input handling, not hardware
compatibility, reconnect behavior or rumble.
