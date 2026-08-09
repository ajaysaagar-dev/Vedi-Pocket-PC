/**
 * deviceInput.ts — domain entity for one input command sent to the PC.
 *
 * This file is part of `veddi-pocketpc-src-additions/`, a drop-in
 * folder that complements the Expo app under `veddi-pocketpc/`. Copy
 * the contents of `veddi-pocketpc-src-additions/domain/` into
 * `veddi-pocketpc/src/domain/` (creating `domain/` if it doesn't
 * exist). After that the use cases below can be imported from
 * `'../domain/use-cases/sendInput'` etc.
 *
 * The entity mirrors the `InputCommand` discriminated union defined
 * in `packages/agent-core/agent_core/entities/input_command.py`.
 * Adding a new command? Add it there first, then mirror here.
 */

export type Button = 'left' | 'right' | 'middle';

export type DeviceInput =
  | { kind: 'absoluteMove'; x: number; y: number; duration?: number }
  | { kind: 'relativeMove'; dx: number; dy: number; duration?: number }
  | { kind: 'click'; button?: Button; clicks?: number; x?: number; y?: number }
  | { kind: 'scroll'; dx?: number; dy: number }
  | { kind: 'text'; text: string }
  | { kind: 'keyPress'; key: string }
  | { kind: 'hotkey'; keys: string[] };

/**
 * Convert a `DeviceInput` into the JSON wire format the PC agent
 * already speaks. This shape has been stable since v1.0 of the
 * mobile app — do not change field names without bumping the agent
 * version.
 */
export function deviceInputToWire(input: DeviceInput): Record<string, unknown> {
  switch (input.kind) {
    case 'absoluteMove':
      return { type: 'mouse_move_to', x: input.x, y: input.y, duration: input.duration ?? 0 };
    case 'relativeMove':
      return {
        type: 'mouse_move',
        dx: input.dx,
        dy: input.dy,
        duration: input.duration ?? 0,
      };
    case 'click':
      return {
        type: 'mouse_click',
        button: input.button ?? 'left',
        clicks: input.clicks ?? 1,
        x: input.x,
        y: input.y,
      };
    case 'scroll':
      return { type: 'scroll', dx: input.dx ?? 0, dy: input.dy };
    case 'text':
      return { type: 'keyboard_type', text: input.text };
    case 'keyPress':
      return { type: 'key_press', key: input.key };
    case 'hotkey':
      return { type: 'hotkey', keys: input.keys };
  }
}
