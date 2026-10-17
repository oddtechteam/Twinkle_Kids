/**
 * Rotation controller — the single source of truth for the display's yaw.
 *
 *   INITIAL_POSE → ROTATING → INTERACTIVE_PAUSE → ROTATING → INTERACTIVE_PAUSE → …
 *
 * Time only advances when `tick` is called (the stage stops ticking while off-screen), so a
 * hidden hero never "catches up" with a jump. One rotation is exactly 360° with ease-in-out, so
 * it starts and stops at the front-facing pose without a visible jolt.
 */

export type RotationPhase = "initial" | "rotating" | "pause";

export interface RotationTimings {
  initialMs: number;
  rotateMs: number;
  pauseMs: number;
}

export const ROTATION_TIMINGS: RotationTimings = {
  initialMs: 1600,
  rotateMs: 10_000,
  pauseMs: 120_000,
};

const easeInOut = (t: number) => 0.5 - 0.5 * Math.cos(Math.PI * t);

export interface RotationController {
  readonly phase: RotationPhase;
  /** Advance by `dt` ms of visible time; returns the yaw in radians (0 = front-facing). */
  tick(dt: number): number;
}

export function createRotationController(timings: RotationTimings = ROTATION_TIMINGS): RotationController {
  let phase: RotationPhase = "initial";
  let elapsed = 0;

  return {
    get phase() {
      return phase;
    },
    tick(dt) {
      elapsed += dt;
      if ((phase === "initial" && elapsed >= timings.initialMs) || (phase === "pause" && elapsed >= timings.pauseMs)) {
        phase = "rotating";
        elapsed = 0;
      }
      if (phase !== "rotating") return 0;
      if (elapsed >= timings.rotateMs) {
        phase = "pause";
        elapsed = 0;
        return 0;
      }
      return 2 * Math.PI * easeInOut(elapsed / timings.rotateMs);
    },
  };
}
