# phi-map --watch Design

## Overview

`phi-map --watch <logfile>` tails a training log in real-time, parses Phi values,
and renders an ASCII terrain visualization in the terminal.

## Usage

```
phi-map --watch checkpoints/v2_decoder2/train.log
phi-map --watch --interval 5 training.log
```

## Behavior

1. **Tail mode**: Opens logfile with `tail -f` semantics (seek to end, follow new lines).
2. **Parse**: Extract Phi values from lines matching `Phi=<float>` or `phi=<float>`.
3. **Refresh**: Every 5 seconds, clear terminal and redraw.
4. **Display**:
   - Current Phi value displayed large (banner-style ASCII digits).
   - Last 50 Phi values as a sparkline using Unicode block chars (`_.-'^`).
   - Min/max/mean summary line below sparkline.
5. **Collapse detection**: If Phi drops >30% from the rolling max of the last 10 values,
   print `!! COLLAPSE DETECTED: Phi {current} < 0.7 * recent_max {max} !!` in red (ANSI).

## ASCII Output Example

```
  Phi = 71.3

  _..--^^''^^--.._--^^'  [last 50]
  min=41.2  max=73.1  mean=62.8  trend=+1.2/step

  [OK] No collapse detected
```

## Implementation Notes

- Single hexa entrypoint at `anima/core/phi_map.hexa`.
- Add `--watch` flag alongside existing `--laws` subcommand.
- Use hexa-native file watcher or poll-based reader with 1s file check interval.
- Terminal clearing: ANSI escape `\x1b[2J\x1b[H`.
- Sparkline: map Phi values to 5-level chars based on min-max range.
- No external TUI framework needed -- plain stdout with ANSI codes.
