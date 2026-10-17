"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Gesture + message sequencer. Runs only during the interactive pause: one character raises a
 * hand (present / point / welcome), their message appears beside that hand, is held, fades, and
 * the arm relaxes before the other character takes a turn. Never two messages at once.
 */

export type Gesture = "idle" | "present" | "point" | "welcome";
export type Presenter = "girl" | "boy";

export interface Presentation {
  presenter: Presenter | null;
  gesture: Gesture;
  message: number;
  showMessage: boolean;
}

const GESTURES: Gesture[] = ["present", "point", "welcome"];
const TIMING = { lead: 1400, raise: 650, hold: 3600, fade: 450, relax: 2800 };
const REST: Presentation = { presenter: null, gesture: "idle", message: 0, showMessage: false };

export function usePresentation(active: boolean, count: number, still: boolean): Presentation {
  const [state, setState] = useState<Presentation>(REST);
  const nextMessage = useRef(0);

  useEffect(() => {
    if (still || count === 0) return;
    if (!active) {
      setState((s) => (s.gesture === "idle" && !s.showMessage ? s : { ...s, gesture: "idle", showMessage: false }));
      return;
    }

    let cancelled = false;
    const timers: number[] = [];
    const wait = (ms: number) => new Promise<void>((resolve) => timers.push(window.setTimeout(resolve, ms)));

    void (async () => {
      let turn = 0;
      await wait(TIMING.lead);
      while (!cancelled) {
        const presenter: Presenter = turn % 2 === 0 ? "girl" : "boy";
        const gesture = GESTURES[turn % GESTURES.length] as Gesture;
        const message = nextMessage.current++ % count;
        setState({ presenter, gesture, message, showMessage: false });
        await wait(TIMING.raise);
        if (cancelled) break;
        setState((s) => ({ ...s, showMessage: true }));
        await wait(TIMING.hold);
        if (cancelled) break;
        setState((s) => ({ ...s, showMessage: false }));
        await wait(TIMING.fade);
        if (cancelled) break;
        setState((s) => ({ ...s, gesture: "idle" }));
        await wait(TIMING.relax);
        turn++;
      }
    })();

    return () => {
      cancelled = true;
      timers.forEach((t) => window.clearTimeout(t));
    };
  }, [active, count, still]);

  // Reduced motion: one calm, static presentation.
  if (still) return { presenter: "girl", gesture: "present", message: 0, showMessage: count > 0 };
  return state;
}
