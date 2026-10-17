"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";

import { Icon } from "@/components/ui/Icon";
import type { HeroMessage } from "@/lib/content/types";
import { Boy, FigureDefs, Girl } from "./HeroFigures";
import styles from "./HeroStage.module.css";
import { createLookController } from "./interaction";
import { type RotationPhase, createRotationController } from "./rotation";
import { BASE, BOY_BASE, CX, GIRL_BASE, MID, TOP, type Tier, figurePose, flute, rivet, sidePath, surfacePoint } from "./scene";
import { usePresentation } from "./usePresentation";

/**
 * Interactive hero stage.
 *
 * - Rotation controller (rotation.ts) owns the single yaw angle. Every frame the podium details
 *   and both figures are projected from that one angle, so the whole display turns as one
 *   assembly: one eased 360° turn, a two-minute interactive pause, then again.
 * - Look controller (interaction.ts) moves heads and eyes; disabled while rotating.
 * - Presentation sequencer (usePresentation.ts) drives gestures and the message card; it only
 *   runs during the pause.
 *
 * The figures are layered vector art, not 3D models: during the turn they orbit the axis,
 * narrow as they go side-on and cross-fade to their back artwork while facing away.
 */

const FLUTES = 24;
const RIVETS = 18;
const STUDS = 20;

const GIRL_LOOK = { rest: { x: 0.22, y: 0.08 }, glance: { x: -0.75, y: 0.15 } };
const BOY_LOOK = { rest: { x: -0.22, y: 0.08 }, glance: { x: 0.75, y: 0.2 } };

const step = (i: number, n: number) => (i * 2 * Math.PI) / n;

function Sparkle({ x, y, size, delay }: { x: number; y: number; size: number; delay: number }) {
  const s = size;
  return (
    <path
      className={styles.sparkle}
      style={{ animationDelay: `${delay}s` }}
      d={`M${x} ${y - s} Q${x + s * 0.18} ${y - s * 0.18} ${x + s} ${y} Q${x + s * 0.18} ${y + s * 0.18} ${x} ${y + s} Q${x - s * 0.18} ${y + s * 0.18} ${x - s} ${y} Q${x - s * 0.18} ${y - s * 0.18} ${x} ${y - s}Z`}
      fill="url(#tkh-gold)"
    />
  );
}

/** One podium tier: side wall, shading, rotating details, top surface and a fine metallic lip. */
function TierShape({
  tier,
  side,
  top,
  children,
}: {
  tier: Tier;
  side: string;
  top: string;
  children?: ReactNode;
}) {
  return (
    <g>
      <path d={sidePath(tier)} fill={side} />
      <path d={sidePath(tier)} fill="url(#tkh-side-shade)" />
      {children}
      <ellipse cx={CX} cy={tier.cy} rx={tier.rx} ry={tier.ry} fill={top} />
      <ellipse cx={CX} cy={tier.cy} rx={tier.rx - 1} ry={tier.ry - 0.6} fill="none" stroke="url(#tkh-trim)" strokeWidth="1.4" />
      <ellipse cx={CX} cy={tier.cy + 1.4} rx={tier.rx * 0.985} ry={tier.ry * 0.97} fill="none" stroke="#fffdf8" strokeOpacity="0.55" strokeWidth="0.8" />
    </g>
  );
}

/** Soft occlusion where a tier meets the surface below it. */
function Occlusion({ tier }: { tier: Tier }) {
  return <ellipse cx={CX} cy={tier.cy + tier.h} rx={tier.rx * 1.05} ry={tier.ry * 1.08} fill="url(#tkh-occlusion)" />;
}

function MessageCard({ messages, presenter, index, show }: { messages: HeroMessage[]; presenter: "girl" | "boy" | null; index: number; show: boolean }) {
  const message = messages[index];
  if (!message || !presenter) return <div className={styles.cards} />;
  return (
    <div className={styles.cards}>
      <p className={`${styles.card} ${presenter === "girl" ? styles.cardGirl : styles.cardBoy}`} data-show={show}>
        <span className={styles.cardIcon}>
          <Icon name={message.icon} size={14} aria-hidden="true" />
        </span>
        <span className={styles.cardText}>{message.text}</span>
        <span className={styles.cardPointer} />
      </p>
    </div>
  );
}

export function HeroStage({ messages }: { messages: HeroMessage[] }) {
  const stageRef = useRef<HTMLDivElement>(null);
  const figuresRef = useRef<SVGGElement>(null);
  const fluteRefs = useRef<(SVGLineElement | null)[]>([]);
  const rivetRefs = useRef<(SVGEllipseElement | null)[]>([]);
  const studRefs = useRef<(SVGEllipseElement | null)[]>([]);
  const girl = { root: useRef<SVGGElement>(null), front: useRef<SVGGElement>(null), back: useRef<SVGGElement>(null), head: useRef<SVGGElement>(null) };
  const boy = { root: useRef<SVGGElement>(null), front: useRef<SVGGElement>(null), back: useRef<SVGGElement>(null), head: useRef<SVGGElement>(null) };

  // One rotation controller for the lifetime of the component — re-renders never restart it.
  const [rotation] = useState(createRotationController);

  const [phase, setPhase] = useState<RotationPhase>("initial");
  const [visible, setVisible] = useState(false);
  const [still, setStill] = useState(false);
  const presentation = usePresentation(phase === "pause" && visible, messages.length, still);
  const presenterRef = useRef(-1);
  useEffect(() => {
    presenterRef.current = presentation.presenter === "girl" ? 0 : presentation.presenter === "boy" ? 1 : -1;
  }, [presentation.presenter]);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    const fine = window.matchMedia("(hover: hover) and (pointer: fine)");
    const area: HTMLElement = stage.closest("section") ?? stage;
    const look = createLookController([GIRL_LOOK, BOY_LOOK]);

    let raf = 0;
    let last = 0;
    let onScreen = false;
    let currentPhase = rotation.phase;
    let girlInFront = false;

    const drawPodium = (yaw: number) => {
      for (let i = 0; i < FLUTES; i++) {
        const el = fluteRefs.current[i];
        if (!el) continue;
        const g = flute(MID, yaw + step(i, FLUTES));
        el.setAttribute("x1", g.x.toFixed(2));
        el.setAttribute("x2", g.x.toFixed(2));
        el.setAttribute("y1", g.y1.toFixed(2));
        el.setAttribute("y2", g.y2.toFixed(2));
        el.setAttribute("opacity", g.opacity.toFixed(3));
      }
      for (let i = 0; i < RIVETS; i++) {
        const el = rivetRefs.current[i];
        if (!el) continue;
        const g = rivet(BASE, yaw + step(i, RIVETS));
        el.setAttribute("cx", g.x.toFixed(2));
        el.setAttribute("cy", g.y.toFixed(2));
        el.setAttribute("opacity", g.opacity.toFixed(3));
      }
      for (let i = 0; i < STUDS; i++) {
        const el = studRefs.current[i];
        if (!el) continue;
        const p = surfacePoint(TOP, 0.86, yaw + step(i, STUDS));
        el.setAttribute("cx", p.x.toFixed(2));
        el.setAttribute("cy", p.y.toFixed(2));
        el.setAttribute("opacity", (0.45 + 0.55 * ((p.depth + 1) / 2)).toFixed(3));
      }
    };

    const placeFigures = (yaw: number) => {
      const [g, b] = [girl, boy];
      const depths: number[] = [];
      for (const [f, base] of [
        [g, GIRL_BASE],
        [b, BOY_BASE],
      ] as const) {
        const pose = figurePose(base, yaw);
        f.root.current?.setAttribute("transform", pose.transform);
        f.front.current?.setAttribute("opacity", pose.frontOpacity.toFixed(3));
        f.back.current?.setAttribute("opacity", pose.backOpacity.toFixed(3));
        depths.push(pose.depth);
      }
      // Paint the nearer figure last (only touches the DOM when the order flips).
      const front = (depths[0] ?? 0) > (depths[1] ?? 0);
      if (front !== girlInFront && g.root.current && b.root.current && figuresRef.current) {
        figuresRef.current.appendChild(front ? g.root.current : b.root.current);
        girlInFront = front;
      }
    };

    const applyLook = () => {
      const [g, b] = [girl, boy];
      const box = stage.getBoundingClientRect();
      const heads = [g.head.current?.getBoundingClientRect(), b.head.current?.getBoundingClientRect()];
      const looks = look.update(heads, box, presenterRef.current, currentPhase !== "rotating");
      [g, b].forEach((f, i) => {
        const l = looks[i];
        if (!l) return;
        f.root.current?.style.setProperty("--lx", l.x.toFixed(3));
        f.root.current?.style.setProperty("--ly", l.y.toFixed(3));
      });
    };

    const frame = (now: number) => {
      const dt = last ? Math.min(now - last, 64) : 16;
      last = now;
      const yaw = rotation.tick(dt);
      if (rotation.phase !== currentPhase) {
        currentPhase = rotation.phase;
        stage.dataset.phase = currentPhase;
        setPhase(currentPhase);
      }
      drawPodium(yaw);
      placeFigures(yaw);
      applyLook();
      raf = window.requestAnimationFrame(frame);
    };

    const sync = () => {
      window.cancelAnimationFrame(raf);
      raf = 0;
      last = 0;
      const reduced = reduce.matches;
      stage.dataset.mode = fine.matches && !reduced ? "track" : "idle";
      stage.dataset.paused = onScreen && !reduced ? "false" : "true";
      setStill(reduced);
      setVisible(onScreen && !reduced);
      if (reduced) {
        // Stable composition: front-facing, no turning, no automatic motion.
        drawPodium(0);
        placeFigures(0);
        return;
      }
      if (onScreen) raf = window.requestAnimationFrame(frame);
    };

    const onMove = (event: PointerEvent) => {
      if (event.pointerType !== "mouse" || !fine.matches || reduce.matches) return;
      look.setPointer({ x: event.clientX, y: event.clientY });
    };
    const onLeave = () => look.setPointer(null);

    const observer = new IntersectionObserver(
      ([entry]) => {
        onScreen = Boolean(entry?.isIntersecting);
        sync();
      },
      { threshold: 0.05 },
    );
    observer.observe(stage);
    area.addEventListener("pointermove", onMove, { passive: true });
    area.addEventListener("pointerleave", onLeave);
    reduce.addEventListener("change", sync);
    fine.addEventListener("change", sync);

    return () => {
      window.cancelAnimationFrame(raf);
      observer.disconnect();
      area.removeEventListener("pointermove", onMove);
      area.removeEventListener("pointerleave", onLeave);
      reduce.removeEventListener("change", sync);
      fine.removeEventListener("change", sync);
    };
    // The refs and the controller are stable for the component's lifetime.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const girlPose = figurePose(GIRL_BASE, 0);
  const boyPose = figurePose(BOY_BASE, 0);
  const gestureOf = (who: "girl" | "boy") => (presentation.presenter === who ? presentation.gesture : "idle");

  return (
    <div ref={stageRef} className={styles.stage} data-mode="idle" data-paused="true" data-phase="initial" aria-hidden="true">
      <div className={styles.scene}>
        <svg className={styles.svg} viewBox="0 0 640 620" role="presentation" focusable="false">
          <FigureDefs />
          <defs>
            <radialGradient id="tkh-halo" cx="50%" cy="50%" r="50%">
              <stop offset="0" stopColor="#fbe7ea" stopOpacity="0.95" />
              <stop offset="0.65" stopColor="#f5cdd3" stopOpacity="0.32" />
              <stop offset="1" stopColor="#f5cdd3" stopOpacity="0" />
            </radialGradient>
            <radialGradient id="tkh-ground" cx="50%" cy="50%" r="50%">
              <stop offset="0" stopColor="#1c2d52" stopOpacity="0.24" />
              <stop offset="1" stopColor="#1c2d52" stopOpacity="0" />
            </radialGradient>
            <radialGradient id="tkh-occlusion" cx="50%" cy="50%" r="50%">
              <stop offset="0.82" stopColor="#5a3d2a" stopOpacity="0.2" />
              <stop offset="1" stopColor="#5a3d2a" stopOpacity="0" />
            </radialGradient>
            <linearGradient id="tkh-side-shade" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#fffdf8" stopOpacity="0.35" />
              <stop offset="0.35" stopColor="#fffdf8" stopOpacity="0" />
              <stop offset="1" stopColor="#3b2a1e" stopOpacity="0.16" />
            </linearGradient>
            <linearGradient id="tkh-trim" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stopColor="#b8925a" />
              <stop offset="0.35" stopColor="#f1ddb5" />
              <stop offset="0.65" stopColor="#cfa86f" />
              <stop offset="1" stopColor="#a8814a" />
            </linearGradient>
            {/* Base: champagne; middle: blush; top: ivory */}
            <linearGradient id="tkh-side-base" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stopColor="#d3bd9b" />
              <stop offset="0.34" stopColor="#f3e6d1" />
              <stop offset="0.7" stopColor="#e6d3b6" />
              <stop offset="1" stopColor="#c4ab86" />
            </linearGradient>
            <linearGradient id="tkh-side-mid" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stopColor="#dfa2ae" />
              <stop offset="0.34" stopColor="#f8dbe0" />
              <stop offset="0.7" stopColor="#efc2ca" />
              <stop offset="1" stopColor="#d5919f" />
            </linearGradient>
            <linearGradient id="tkh-side-top" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stopColor="#e6d9c6" />
              <stop offset="0.34" stopColor="#fffbf5" />
              <stop offset="0.7" stopColor="#f5ecdf" />
              <stop offset="1" stopColor="#dccbb1" />
            </linearGradient>
            <radialGradient id="tkh-top-base" cx="42%" cy="34%" r="75%">
              <stop offset="0" stopColor="#f9efe0" />
              <stop offset="1" stopColor="#e3cfb0" />
            </radialGradient>
            <radialGradient id="tkh-top-mid" cx="42%" cy="34%" r="75%">
              <stop offset="0" stopColor="#fdf0f2" />
              <stop offset="1" stopColor="#efc4cc" />
            </radialGradient>
            <radialGradient id="tkh-top-top" cx="42%" cy="30%" r="78%">
              <stop offset="0" stopColor="#ffffff" />
              <stop offset="0.7" stopColor="#fbf5ec" />
              <stop offset="1" stopColor="#efe3d0" />
            </radialGradient>
          </defs>

          <circle cx="320" cy="320" r="270" fill="url(#tkh-halo)" />
          <Sparkle x={104} y={138} size={8} delay={0} />
          <Sparkle x={552} y={112} size={7} delay={1.2} />
          <Sparkle x={70} y={420} size={5.5} delay={2.1} />
          <Sparkle x={580} y={430} size={6.5} delay={0.6} />

          {/* Podium: three tiers that turn together (details projected from the same yaw) */}
          <ellipse cx={CX} cy="594" rx="296" ry="24" fill="url(#tkh-ground)" />
          <TierShape tier={BASE} side="url(#tkh-side-base)" top="url(#tkh-top-base)">
            <path d={`M${CX - BASE.rx} ${BASE.cy + 8} A${BASE.rx} ${BASE.ry} 0 0 0 ${CX + BASE.rx} ${BASE.cy + 8}`} fill="none" stroke="url(#tkh-trim)" strokeWidth="1" opacity="0.7" />
            {Array.from({ length: RIVETS }, (_, i) => {
              const g = rivet(BASE, step(i, RIVETS));
              return (
                <ellipse
                  key={i}
                  ref={(el) => {
                    rivetRefs.current[i] = el;
                  }}
                  cx={g.x}
                  cy={g.y}
                  rx="2.2"
                  ry="2.2"
                  opacity={g.opacity}
                  fill="url(#tkh-gold)"
                />
              );
            })}
          </TierShape>
          <Occlusion tier={MID} />
          <TierShape tier={MID} side="url(#tkh-side-mid)" top="url(#tkh-top-mid)">
            {Array.from({ length: FLUTES }, (_, i) => {
              const g = flute(MID, step(i, FLUTES));
              return (
                <line
                  key={i}
                  ref={(el) => {
                    fluteRefs.current[i] = el;
                  }}
                  x1={g.x}
                  x2={g.x}
                  y1={g.y1}
                  y2={g.y2}
                  opacity={g.opacity}
                  stroke="#fffaf6"
                  strokeWidth="1.1"
                />
              );
            })}
          </TierShape>
          <Occlusion tier={TOP} />
          <TierShape tier={TOP} side="url(#tkh-side-top)" top="url(#tkh-top-top)" />
          <ellipse cx={CX} cy={TOP.cy} rx={TOP.rx * 0.93} ry={TOP.ry * 0.93} fill="none" stroke="#cfa86f" strokeOpacity="0.4" strokeWidth="0.8" />
          {Array.from({ length: STUDS }, (_, i) => {
            const p = surfacePoint(TOP, 0.86, step(i, STUDS));
            return (
              <ellipse
                key={i}
                ref={(el) => {
                  studRefs.current[i] = el;
                }}
                cx={p.x}
                cy={p.y}
                rx="2.6"
                ry="1.2"
                opacity={0.45 + 0.55 * ((p.depth + 1) / 2)}
                fill="url(#tkh-gold)"
              />
            );
          })}

          <g ref={figuresRef}>
            <Girl
              transform={girlPose.transform}
              gesture={gestureOf("girl")}
              rest={GIRL_LOOK.rest}
              className={styles.figure}
              rootRef={girl.root}
              frontRef={girl.front}
              backRef={girl.back}
              headRef={girl.head}
            />
            <Boy
              transform={boyPose.transform}
              gesture={gestureOf("boy")}
              rest={BOY_LOOK.rest}
              className={styles.figure}
              rootRef={boy.root}
              frontRef={boy.front}
              backRef={boy.back}
              headRef={boy.head}
            />
          </g>
        </svg>
      </div>
      <MessageCard messages={messages} presenter={presentation.presenter} index={presentation.message} show={presentation.showMessage} />
    </div>
  );
}
