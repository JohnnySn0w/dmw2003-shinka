# Normal and Digivolution progression

Reconstructed from the supported European executable and reward overlay. These
are cumulative thresholds, not the EXP required for just the preceding level.
The readable formulas in `tools/progression_math.py` are analysis aids; the game
continues to run its original level-up routines.

## Rookie levels: cubic, with different growth coefficients

For target level L from 2 to 99, the minimum total EXP is:

`floor(g * (L^3 + 5*L - 6) / 10) + band(L) + 1`

The final +1 reflects the original strict comparison. Level 1 starts at zero.
`band(L)` is 0 below level 5, 50 at 5-19, 800 at 20-39, and 3000 at 40-99.

| Rookie | g | Level 5 | Level 20 | Level 40 | Level 99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Monmon | 6 | 137 | 5,657 | 41,517 | 585,473 |
| Guilmon / Renamon | 7 | 151 | 6,466 | 47,936 | 682,552 |
| Kotemon / Veemon | 8 | 166 | 7,276 | 54,356 | 779,631 |
| Agumon / Patamon | 9 | 180 | 8,085 | 60,775 | 876,710 |
| Kumamon | 10 | 195 | 8,895 | 67,195 | 973,789 |

The total EXP storage cap is 999,999; rookie level stops at 99. The multiplier
changes awards, not these thresholds. Normal awards use the enemy's normal EXP
field, scaled before the original participation split: full for one participant,
60% each for two, integer division by three for three.

## Digivolution skill: mostly linear, with a level-dependent award

Let C be the form's natural growth limit. The minimum total DV EXP for skill
level L is:

`10 * min(L-1, C-1) + 50 * max(0, L-C)`

Early forms such as Grizzmon have C=100, so each skill level costs 10 points all
the way to the maximum level 99 (980 cumulative DV EXP). Some later forms have
lower limits; levels after that limit cost 50 points each. For example, C=60
means level 60 costs 590 cumulative points and level 61 costs 640.

The original award to a participating form is calculated separately:

1. `raw = floor(10 * enemy_DV_base / min(rookie_level, 50))`.
2. With two participating forms, use `floor(raw * 6 / 10)`; with more than two,
   use `floor(raw / participant_count)`.
3. Clamp to at least 1 and at most 10 below the form's natural limit, or 50 at
   and above that limit.
4. Shinka's independent multiplier scales this **final** amount.

Thus a 3x setting awards 3-30 points below the limit, or 3-150 beyond it.
Cumulative DV EXP carries over between levels; the routine can award multiple
levels. Skill level remains capped at 99 and stored DV EXP at 9,999,999.

Against Kunemon (DV base 1), a lone form gets 2 points with a level-5 rookie,
but only 1 with a level-10 rookie. At 3x these become 6 and 3 respectively.
Faster normal leveling can therefore reduce DV gains from the same enemies;
normal and DV multipliers need separate controls.

## Evidence and limits

- Reward overlay load base: `0x80082cb0`; verified SHA-256 is recorded in
  [experience.md](experience.md).
- Rookie threshold/level loop: overlay offsets `0x34d4..0x3698`.
- DV award calculation: overlay offset `0x3c74`; final delivery call: `0x1388`.
- DV accumulation and skill-level loop: overlay offset `0x3910`.
- Executable profile table: RAM `0x8003ef5c`, stride `0x58`; growth coefficient
  at `+0x3e`, natural form limit at `+0x3c`.
- A copied test save exercised Kumamon reaching level 5 and unlocking Grizzmon
  through the game's own reward logic, then a Grizzmon battle receiving 2
  original DV points from Kunemon.

The formula reconstruction is broader than live test coverage. Later forms,
multi-form participation and campaign-wide unlock behavior still need tests.


## Multiple levels from one award

Both inspected routines loop, rather than stopping after the first level:
normal EXP branches from overlay offset `0x366c` back to `0x3568` after a
successful increment and runs the per-level growth call at `0x362c`. DV branches
from `0x3a1c` back to `0x39a8`, retaining cumulative EXP and testing the next
threshold until it fails or reaches level 99. These are static code findings;
result-screen presentation and all multi-level unlock combinations have not
been exhaustively tested live.

The optional fixed-10 DV mode replaces step 4 above with an award of 10,
regardless of the enemy, rookie level or participation split. Eligibility is
unchanged. It normally produces one skill level per battle until the natural
limit and one per five battles afterward, without relying on multi-level gains.
