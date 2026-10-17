/**
 * Look controller — where each character's head and eyes point (values −1…1, written to the
 * `--lx` / `--ly` custom properties). Independent of the rotation controller: while the display
 * rotates the stage disables looking, so both faces settle forward and nothing fights the turn.
 */

export interface Look {
  x: number;
  y: number;
}

export interface LookFigure {
  /** Relaxed resting gaze. */
  rest: Look;
  /** Gaze used while this character presents a message (towards their hand). */
  glance: Look;
}

const clamp = (v: number, limit: number) => Math.max(-limit, Math.min(limit, v));
const FORWARD: Look = { x: 0, y: 0 };

export function createLookController(figures: LookFigure[]) {
  const current = figures.map((f) => ({ ...f.rest }));
  let pointer: { x: number; y: number } | null = null;

  return {
    setPointer(next: { x: number; y: number } | null) {
      pointer = next;
    },

    /**
     * @param heads   on-screen centre of each head (only needed while a pointer is active)
     * @param area    the character display area, used to scale the look distance
     * @param presenter index of the presenting character, or −1
     * @param enabled false while rotating (faces settle forward)
     */
    update(heads: (DOMRect | undefined)[], area: DOMRect, presenter: number, enabled: boolean): Look[] {
      figures.forEach((figure, i) => {
        let target: Look = figure.rest;
        if (!enabled) target = FORWARD;
        else if (pointer && heads[i]) {
          const head = heads[i] as DOMRect;
          target = {
            x: clamp((pointer.x - (head.left + head.width / 2)) / (area.width * 0.45), 1),
            y: clamp((pointer.y - (head.top + head.height / 2)) / (area.height * 0.5), 0.8),
          };
        } else if (presenter === i) target = figure.glance;
        const c = current[i] as Look;
        c.x += (target.x - c.x) * 0.09;
        c.y += (target.y - c.y) * 0.09;
      });
      return current;
    },
  };
}
