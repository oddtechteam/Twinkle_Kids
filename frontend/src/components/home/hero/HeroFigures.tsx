import type { CSSProperties, ReactNode, Ref } from "react";

import styles from "./HeroStage.module.css";

/**
 * Hand-built vector fashion figures (no external assets). Each figure is drawn in its own
 * coordinate space with the feet centred on (0, 0), body going up (negative y).
 *
 * Layers that move:
 *   - head / features / pupils / lids → cursor-following (`--lx`, `--ly`) and blinking
 *   - arms → shoulder ▸ elbow ▸ wrist joints driven by the figure's `data-gesture`
 *   - front / back artwork → cross-faded by the stage while the display rotates
 */

const SKIN = "#f2c8ab";
const SKIN_SHADE = "#e3ab8c";
const SKIN_LINE = "#d0917a";
const LINE = "#6e4436";

export function FigureDefs() {
  return (
    <defs>
      <radialGradient id="tkh-face" cx="44%" cy="36%" r="72%">
        <stop offset="0" stopColor="#fde6d5" />
        <stop offset="0.58" stopColor="#f4cbb0" />
        <stop offset="1" stopColor="#e3aa8a" />
      </radialGradient>
      <radialGradient id="tkh-iris" cx="38%" cy="34%" r="72%">
        <stop offset="0" stopColor="#7a5340" />
        <stop offset="1" stopColor="#2b1c16" />
      </radialGradient>
      <linearGradient id="tkh-hair-girl" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#7a4e35" />
        <stop offset="1" stopColor="#4b2d1e" />
      </linearGradient>
      <linearGradient id="tkh-hair-boy" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#5b3e2c" />
        <stop offset="1" stopColor="#33241a" />
      </linearGradient>
      <linearGradient id="tkh-blush" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stopColor="#e3a0ae" />
        <stop offset="0.36" stopColor="#f8d3da" />
        <stop offset="0.66" stopColor="#f2bdc8" />
        <stop offset="1" stopColor="#dc93a3" />
      </linearGradient>
      <linearGradient id="tkh-ruffle" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#fbe4e8" />
        <stop offset="1" stopColor="#f6d0d7" />
      </linearGradient>
      <linearGradient id="tkh-cream" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stopColor="#efe3d3" />
        <stop offset="0.4" stopColor="#fffaf3" />
        <stop offset="1" stopColor="#ebdcc8" />
      </linearGradient>
      <linearGradient id="tkh-champagne" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#f2e1c2" />
        <stop offset="0.55" stopColor="#dcc093" />
        <stop offset="1" stopColor="#bf9b64" />
      </linearGradient>
      <linearGradient id="tkh-rose" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#efa3b1" />
        <stop offset="1" stopColor="#c96b81" />
      </linearGradient>
      <linearGradient id="tkh-ivory" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stopColor="#e9dfcd" />
        <stop offset="0.38" stopColor="#fffbf4" />
        <stop offset="0.7" stopColor="#f6efe2" />
        <stop offset="1" stopColor="#e2d5bf" />
      </linearGradient>
      <linearGradient id="tkh-navy" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stopColor="#1a2a4c" />
        <stop offset="0.4" stopColor="#33487a" />
        <stop offset="1" stopColor="#192848" />
      </linearGradient>
      <linearGradient id="tkh-gold" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#f1dcb2" />
        <stop offset="0.5" stopColor="#cfa86f" />
        <stop offset="1" stopColor="#ad8448" />
      </linearGradient>
      <linearGradient id="tkh-shoe-champagne" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#efdcbc" />
        <stop offset="1" stopColor="#c7a674" />
      </linearGradient>
      <linearGradient id="tkh-shoe-navy" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#3a4f80" />
        <stop offset="1" stopColor="#1b2a4a" />
      </linearGradient>
      <pattern id="tkh-knit" width="4" height="3" patternUnits="userSpaceOnUse">
        <path d="M0 1.5 H4" stroke="#d9cbb3" strokeWidth="0.6" />
      </pattern>
      <radialGradient id="tkh-contact" cx="50%" cy="50%" r="50%">
        <stop offset="0" stopColor="#1c2d52" stopOpacity="0.34" />
        <stop offset="0.6" stopColor="#1c2d52" stopOpacity="0.12" />
        <stop offset="1" stopColor="#1c2d52" stopOpacity="0" />
      </radialGradient>
    </defs>
  );
}

// --- Shared parts ------------------------------------------------------------------------------

/** Fuller, child-like face: softly rounded cheeks below the eye line. */
const FACE = "M0 -37 C21 -37 35 -22 35 -2 C35 19 22 34 0 34 C-22 34 -35 19 -35 -2 C-35 -22 -21 -37 0 -37Z";

/** Eye: the pupil is clipped to the eye white so it can never leave the socket. */
function Eye({ id, x, lashes = false }: { id: string; x: number; lashes?: boolean }) {
  return (
    <g transform={`translate(${x} -2)`}>
      <clipPath id={id}>
        <ellipse rx="6.6" ry="7.6" />
      </clipPath>
      <ellipse rx="6.6" ry="7.6" fill="#fffdfb" />
      <g clipPath={`url(#${id})`}>
        <g className={styles.pupil}>
          <circle r="4.6" fill="url(#tkh-iris)" />
          <circle r="2" fill="#1d130f" />
          <circle cx="1.6" cy="-1.8" r="1.5" fill="#fff" />
          <circle cx="-1.6" cy="1.6" r="0.7" fill="#fff" opacity="0.7" />
        </g>
      </g>
      <ellipse className={styles.lid} rx="7.2" ry="8.2" fill={SKIN} />
      <path d="M-7 -1.2 Q0 -10.2 7 -1.2" fill="none" stroke={LINE} strokeWidth="1.6" strokeLinecap="round" />
      {lashes && (
        <path
          d={x < 0 ? "M-6.6 -2.6 l-2.8 -2 M-4.8 -5.4 l-1.6 -2.6" : "M6.6 -2.6 l2.8 -2 M4.8 -5.4 l1.6 -2.6"}
          stroke={LINE}
          strokeWidth="1.3"
          strokeLinecap="round"
        />
      )}
    </g>
  );
}

/** Hand drawn at the wrist (0, 0) pointing down. `inner` = side the thumb faces (towards the body). */
function OpenHand({ inner }: { inner: number }) {
  return (
    <>
      <path d="M-6.3 0 C-7.6 5 -7.2 10.6 -5.5 14.2 C-3.8 17.8 3.8 17.8 5.5 14.2 C7.2 10.6 7.6 5 6.3 0Z" fill={SKIN} />
      <path d="M-2.7 11.6 V16 M0 12.2 V16.9 M2.7 11.6 V16" stroke={SKIN_LINE} strokeWidth="0.9" strokeLinecap="round" opacity="0.75" />
      <path d={`M${inner * 5.6} 2.8 C${inner * 9.8} 5.2 ${inner * 9.6} 9.2 ${inner * 7.2} 11.2`} fill="none" stroke={SKIN} strokeWidth="4.4" strokeLinecap="round" />
      <path d={`M${inner * 6.6} 6 C${inner * 7.4} 7.4 ${inner * 7.4} 8.6 ${inner * 6.8} 9.8`} fill="none" stroke={SKIN_LINE} strokeWidth="0.8" opacity="0.6" />
    </>
  );
}

function PointHand({ inner }: { inner: number }) {
  return (
    <>
      <path d="M-6 0 C-7.2 4 -6.8 9 -4.8 11 C-2.4 12.8 3 12.8 5.2 10.6 C7 8 7.2 4 6.2 0Z" fill={SKIN} />
      <path d={`M${-inner * 1.6} 10 L${-inner * 1.6} 22.5`} stroke={SKIN} strokeWidth="4.4" strokeLinecap="round" />
      <path d="M-4 7.4 Q0 9 4 7.4" fill="none" stroke={SKIN_LINE} strokeWidth="0.8" opacity="0.7" />
      <path d={`M${inner * 5.4} 3 C${inner * 8.6} 5 ${inner * 8.2} 8 ${inner * 5.6} 9`} fill="none" stroke={SKIN} strokeWidth="4" strokeLinecap="round" />
    </>
  );
}

/**
 * Jointed arm anchored at the shoulder. `side` is +1 for the arm on the figure's +x side and −1
 * for the −x side; joint angles come from CSS (`--sh`, `--el`, `--wr`) so gestures transition
 * smoothly. `role` = "lead" (presents), "support" (joins the welcome) or "still" (back view).
 */
function Arm({
  x,
  y,
  side,
  upper,
  fore,
  width,
  role,
  sleeve,
}: {
  x: number;
  y: number;
  side: 1 | -1;
  upper: number;
  fore: number;
  width: number;
  role: "lead" | "support" | "still";
  sleeve: ReactNode;
}) {
  const roleClass = role === "lead" ? styles.lead : role === "support" ? styles.support : "";
  return (
    <g transform={`translate(${x} ${y})`}>
      <g className={`${styles.shoulder} ${roleClass}`} style={{ "--dir": side } as CSSProperties}>
        <path d={`M0 0 L0 ${upper}`} stroke={SKIN} strokeWidth={width} strokeLinecap="round" />
        <g transform={`translate(0 ${upper})`}>
          <g className={styles.elbow}>
            <path d={`M0 0 L0 ${fore}`} stroke={SKIN} strokeWidth={width - 1} strokeLinecap="round" />
            <g transform={`translate(0 ${fore})`}>
              <g className={styles.wrist}>
                <g className={styles.handOpen}>
                  <OpenHand inner={-side} />
                </g>
                {role === "lead" && (
                  <g className={styles.handPoint}>
                    <PointHand inner={-side} />
                  </g>
                )}
              </g>
            </g>
          </g>
        </g>
        <g transform={`scale(${side} 1)`}>{sleeve}</g>
      </g>
    </g>
  );
}

function Floret({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <g fill="url(#tkh-gold)">
        <circle cx="0" cy="-1.6" r="1.1" />
        <circle cx="1.5" cy="-0.5" r="1.1" />
        <circle cx="0.9" cy="1.3" r="1.1" />
        <circle cx="-0.9" cy="1.3" r="1.1" />
        <circle cx="-1.5" cy="-0.5" r="1.1" />
      </g>
      <circle r="0.8" fill="#d97a8f" />
    </g>
  );
}

export interface FigureRefs {
  rootRef: Ref<SVGGElement>;
  frontRef: Ref<SVGGElement>;
  backRef: Ref<SVGGElement>;
  headRef: Ref<SVGGElement>;
}

interface FigureProps extends FigureRefs {
  transform: string;
  gesture: string;
  rest: { x: number; y: number };
  className: string;
}

const restStyle = (rest: { x: number; y: number }) => ({ "--lx": rest.x, "--ly": rest.y }) as CSSProperties;

// --- Girl --------------------------------------------------------------------------------------

function GirlLegs({ back = false }: { back?: boolean }) {
  return (
    <>
      <path d="M-12 -112 L-13.5 -20 M12 -112 L13.5 -20" stroke={SKIN} strokeWidth="15.5" strokeLinecap="round" />
      <path d="M-13.5 -38 L-13.5 -14 M13.5 -38 L13.5 -14" stroke="#fffaf3" strokeWidth="16.5" strokeLinecap="round" />
      <path d="M-22 -39 q2.8 -3.2 5.6 0 q2.8 -3.2 5.6 0 q2.8 -3.2 5.6 0 M5.2 -39 q2.8 -3.2 5.6 0 q2.8 -3.2 5.6 0 q2.8 -3.2 5.6 0" fill="none" stroke="#efd6da" strokeWidth="1.8" strokeLinecap="round" />
      {[-1, 1].map((s) => (
        <g key={s} transform={`translate(${s * 2} 0) scale(${-s} 1)`}>
          {back ? (
            <path d="M-14 -15 C-21 -15 -25 -10 -25 -5 C-25 -1.5 -23 0 -20 0 H-8 C-5 0 -3 -1.5 -3 -5 C-3 -10 -7 -15 -14 -15Z" fill="url(#tkh-shoe-champagne)" />
          ) : (
            <>
              <path d="M-14 -17 C-23 -17 -28 -10 -28 -5 C-28 -1.5 -26 0 -22 0 H-6 C-2 0 0 -1.5 0 -5 C0 -10 -5 -17 -14 -17Z" fill="url(#tkh-shoe-champagne)" />
              <path d="M-22 -13 Q-14 -10 -6 -13" fill="none" stroke="#b8945f" strokeWidth="2.2" strokeLinecap="round" />
              <circle cx="-7.6" cy="-12.6" r="1.5" fill="url(#tkh-gold)" />
              <ellipse cx="-20" cy="-8" rx="3.2" ry="1.4" fill="#fff" opacity="0.45" />
            </>
          )}
          <path d={back ? "M-25 -1.8 H-3" : "M-28 -2 H0"} stroke="#a88456" strokeWidth="2.2" />
        </g>
      ))}
    </>
  );
}

function GirlSkirt() {
  return (
    <>
      <path
        d="M-27 -192 C-41 -160 -65 -132 -88 -100 Q-76 -93 -66 -99 Q-55 -91 -44 -98 Q-33 -90 -22 -97 Q-11 -89 0 -96 Q11 -89 22 -97 Q33 -90 44 -98 Q55 -91 66 -99 Q76 -93 88 -100 C65 -132 41 -160 27 -192Z"
        fill="#fffaf6"
      />
      <path
        d="M-25 -204 C-32 -170 -57 -140 -83 -108 Q-73 -100 -62 -106 Q-52 -98 -41 -105 Q-31 -97 -20 -104 Q-10 -96 0 -103 Q10 -96 20 -104 Q31 -97 41 -105 Q52 -98 62 -106 Q73 -100 83 -108 C57 -140 32 -170 25 -204Z"
        fill="url(#tkh-blush)"
      />
      {/* Lower ruffle tier */}
      <path
        d="M-58 -136 Q-29 -129 0 -132 Q29 -129 58 -136 C66 -126 75 -117 83 -108 Q73 -100 62 -106 Q52 -98 41 -105 Q31 -97 20 -104 Q10 -96 0 -103 Q-10 -96 -20 -104 Q-31 -97 -41 -105 Q-52 -98 -62 -106 Q-73 -100 -83 -108 C-75 -117 -66 -126 -58 -136Z"
        fill="url(#tkh-ruffle)"
      />
      <path d="M-44 -128 Q-48 -118 -51 -106 M-22 -126 Q-24 -116 -25 -104 M0 -127 V-104 M22 -126 Q24 -116 25 -104 M44 -128 Q48 -118 51 -106" fill="none" stroke="#dc93a3" strokeWidth="1.1" opacity="0.4" />
      {/* Pleats on the upper tier */}
      <path d="M-8 -200 Q-12 -168 -17 -134 M8 -200 Q12 -168 17 -134 M-17 -198 Q-27 -166 -38 -134 M17 -198 Q27 -166 38 -134" fill="none" stroke="#c87185" strokeWidth="1.2" opacity="0.32" />
      {/* Embroidered band */}
      <path d="M-58 -136 Q-29 -129 0 -132 Q29 -129 58 -136" fill="none" stroke="#fffaf3" strokeWidth="3.4" />
      {[-46, -27, -9, 9, 27, 46].map((x) => (
        <Floret key={x} x={x} y={x === -9 || x === 9 ? -131.6 : -133} />
      ))}
    </>
  );
}

function GirlSleeve() {
  return (
    <>
      <ellipse cx="2" cy="3" rx="13.5" ry="12.5" fill="url(#tkh-cream)" />
      <path d="M-6 -4 Q-1 2 -2 12 M4 -6 Q8 1 7 12" fill="none" stroke="#e2d2bd" strokeWidth="1" opacity="0.8" />
      <path d="M-9.5 12.5 q11 5 22.5 0" fill="none" stroke="#efb3bf" strokeWidth="2.6" strokeLinecap="round" />
    </>
  );
}

function GirlFront({ headRef }: { headRef: Ref<SVGGElement> }) {
  return (
    <>
      <g className={styles.body}>
        <GirlLegs />
        <GirlSkirt />
        <path d="M-8 -272 h16 v22 q-8 5 -16 0z" fill={SKIN_SHADE} />
        <path d="M-29 -252 C-31 -232 -28 -214 -25 -202 H25 C28 -214 31 -232 29 -252 C15 -259 -15 -259 -29 -252Z" fill="url(#tkh-blush)" />
        <path
          d="M-24 -240 q3 -2.2 6 0 t6 0 t6 0 t6 0 t6 0 t6 0 t6 0 t6 0 M-24 -232 q3 -2.2 6 0 t6 0 t6 0 t6 0 t6 0 t6 0 t6 0 t6 0 M-23 -224 q3 -2.2 6 0 t6 0 t6 0 t6 0 t6 0 t6 0 t6 0 t5 0"
          fill="none"
          stroke="#c87185"
          strokeWidth="0.9"
          opacity="0.42"
        />
        {/* Champagne sash with a rose rosette */}
        <rect x="-26" y="-210" width="52" height="10" rx="4.5" fill="url(#tkh-champagne)" />
        <path d="M-25 -206.5 H25" stroke="#fff6e6" strokeWidth="1" opacity="0.7" />
        <g transform="translate(-15 -205)">
          <circle r="6.4" fill="url(#tkh-rose)" />
          <path d="M0 -3.4 C3 -3.4 3.6 0 1.6 1.6 C-0.6 3.2 -3.4 1.4 -2.8 -1.2" fill="none" stroke="#fbe0e6" strokeWidth="1.1" />
        </g>
        {/* Arms: the girl presents with her outer (left on screen) hand */}
        <Arm x={-29} y={-248} side={-1} upper={40} fore={33} width={12.5} role="lead" sleeve={<GirlSleeve />} />
        <Arm x={29} y={-248} side={1} upper={40} fore={33} width={12.5} role="support" sleeve={<GirlSleeve />} />
        {/* Peter Pan collar with gold embroidery */}
        <path d="M-1 -257 C-4 -244 -18 -241 -21 -252 C-14 -257 -7 -258 -1 -257Z" fill="url(#tkh-cream)" />
        <path d="M1 -257 C4 -244 18 -241 21 -252 C14 -257 7 -258 1 -257Z" fill="url(#tkh-cream)" />
        <g fill="#cfa86f">
          <circle cx="-15" cy="-248.5" r="0.9" />
          <circle cx="-10" cy="-246.6" r="0.9" />
          <circle cx="-5" cy="-247.4" r="0.9" />
          <circle cx="15" cy="-248.5" r="0.9" />
          <circle cx="10" cy="-246.6" r="0.9" />
          <circle cx="5" cy="-247.4" r="0.9" />
        </g>
      </g>

      <g ref={headRef} className={`${styles.head} ${styles.girlHead}`}>
        <g transform="translate(0 -300)">
          <path d="M-40 4 C-46 -32 -27 -52 0 -52 C27 -52 46 -32 40 4 C39 20 34 30 27 36 C20 40 -20 40 -27 36 C-34 30 -39 20 -40 4Z" fill="url(#tkh-hair-girl)" />
          <path d="M-38 2 C-43 16 -40 30 -31 39 C-30 30 -30 20 -31 10Z M38 2 C43 16 40 30 31 39 C30 30 30 20 31 10Z" fill="#5a3726" />
          <circle cx="0" cy="-54" r="18" fill="url(#tkh-hair-girl)" />
          <path d="M-10 -63 q10 -7 20 0 M-12 -54 q12 -6 24 0" fill="none" stroke="#956246" strokeWidth="1.6" strokeLinecap="round" opacity="0.6" />
          <ellipse cx="-34.5" cy="4" rx="5.6" ry="7.6" fill={SKIN_SHADE} />
          <ellipse cx="34.5" cy="4" rx="5.6" ry="7.6" fill={SKIN_SHADE} />
          <path d={FACE} fill="url(#tkh-face)" />
          <g className={styles.features}>
            <path d="M-19.5 -13.5 q6 -3.6 12 -0.6 M7.5 -14.1 q6 -3 12 0.6" fill="none" stroke="#6a4430" strokeWidth="2" strokeLinecap="round" />
            <Eye id="tkh-eye-gl" x={-12.5} lashes />
            <Eye id="tkh-eye-gr" x={12.5} lashes />
            <path d="M-2.2 8.6 q2.2 2.2 4.4 0" fill="none" stroke={SKIN_LINE} strokeWidth="1.6" strokeLinecap="round" />
            <path d="M-9 15 Q0 26 9 15 Q0 19 -9 15Z" fill="#d6667b" />
            <path d="M-5.6 16.6 Q0 19.2 5.6 16.6" fill="none" stroke="#fff" strokeWidth="1.4" strokeLinecap="round" />
            <ellipse cx="-20.5" cy="12" rx="7" ry="5" fill="#f29aa8" opacity="0.45" />
            <ellipse cx="20.5" cy="12" rx="7" ry="5" fill="#f29aa8" opacity="0.45" />
          </g>
          <g className={styles.hairFront}>
            <path
              d="M-35 -4 C-38 -33 -19 -48 2 -47 C23 -46 38 -32 35 -2 C32 -14 26 -21 16 -23 C9 -15 -3 -12 -14 -14 C-23 -15 -30 -10 -35 -4Z"
              fill="url(#tkh-hair-girl)"
            />
            <path d="M-26 -30 Q-12 -42 6 -40 M10 -38 Q24 -34 30 -18" fill="none" stroke="#956246" strokeWidth="1.3" strokeLinecap="round" opacity="0.6" />
            <g transform="translate(14 -44) rotate(18)">
              <path d="M0 0 C-11 -11 -18 -2 -15 4 C-12 10 -5 6 0 0Z M0 0 C11 -11 18 -2 15 4 C12 10 5 6 0 0Z" fill="url(#tkh-rose)" />
              <path d="M-12 1 Q-7 2 -2 0 M12 1 Q7 2 2 0" fill="none" stroke="#fbe0e6" strokeWidth="0.9" opacity="0.8" />
              <circle r="3.4" fill="#c96b81" />
            </g>
          </g>
        </g>
      </g>
    </>
  );
}

function GirlBack() {
  return (
    <>
      <g className={styles.body}>
        <GirlLegs back />
        <GirlSkirt />
        <path d="M-8 -272 h16 v22 q-8 5 -16 0z" fill={SKIN_SHADE} />
        <path d="M-29 -252 C-31 -232 -28 -214 -25 -202 H25 C28 -214 31 -232 29 -252 C15 -259 -15 -259 -29 -252Z" fill="url(#tkh-blush)" />
        <path d="M0 -254 V-210" stroke="#d48fa0" strokeWidth="1" opacity="0.6" />
        <g fill="#fffaf3">
          <circle cx="0" cy="-246" r="1.7" />
          <circle cx="0" cy="-237" r="1.7" />
          <circle cx="0" cy="-228" r="1.7" />
          <circle cx="0" cy="-219" r="1.7" />
        </g>
        <path d="M-16 -256 Q0 -247 16 -256 Q0 -251 -16 -256Z" fill="url(#tkh-cream)" />
        <rect x="-26" y="-210" width="52" height="10" rx="4.5" fill="url(#tkh-champagne)" />
        {/* Sash bow at the back */}
        <g transform="translate(0 -205)">
          <path d="M-2 2 L-11 32 M2 2 L10 30" stroke="url(#tkh-champagne)" strokeWidth="4.6" strokeLinecap="round" />
          <path d="M0 0 C-16 -14 -27 -2 -22 6 C-18 13 -8 8 0 0Z M0 0 C16 -14 27 -2 22 6 C18 13 8 8 0 0Z" fill="url(#tkh-champagne)" />
          <ellipse rx="4" ry="4.6" fill="#c9a873" />
        </g>
        <Arm x={-29} y={-248} side={-1} upper={40} fore={33} width={12.5} role="still" sleeve={<GirlSleeve />} />
        <Arm x={29} y={-248} side={1} upper={40} fore={33} width={12.5} role="still" sleeve={<GirlSleeve />} />
      </g>
      <g transform="translate(0 -300)">
        <path d="M-40 2 C-46 -34 -27 -53 0 -53 C27 -53 46 -34 40 2 C39 22 33 33 24 38 C14 42 -14 42 -24 38 C-33 33 -39 22 -40 2Z" fill="url(#tkh-hair-girl)" />
        <path d="M-26 -30 Q-18 0 -20 30 M-10 -40 Q-6 0 -8 36 M10 -40 Q6 0 8 36 M26 -30 Q18 0 20 30" fill="none" stroke="#956246" strokeWidth="1.3" opacity="0.45" />
        <circle cx="0" cy="-54" r="18" fill="url(#tkh-hair-girl)" />
        <g transform="translate(0 -38)">
          <path d="M0 0 C-11 -11 -18 -2 -15 4 C-12 10 -5 6 0 0Z M0 0 C11 -11 18 -2 15 4 C12 10 5 6 0 0Z" fill="url(#tkh-rose)" />
          <circle r="3.4" fill="#c96b81" />
        </g>
      </g>
    </>
  );
}

export function Girl({ transform, gesture, rest, className, rootRef, frontRef, backRef, headRef }: FigureProps) {
  return (
    <g ref={rootRef} transform={transform} style={restStyle(rest)} data-gesture={gesture} className={className}>
      <ellipse cx="0" cy="1" rx="40" ry="7.5" fill="url(#tkh-contact)" />
      <g ref={frontRef}>
        <GirlFront headRef={headRef} />
      </g>
      <g ref={backRef} opacity="0">
        <GirlBack />
      </g>
    </g>
  );
}

// --- Boy ---------------------------------------------------------------------------------------

function BoyLegs({ back = false }: { back?: boolean }) {
  return (
    <>
      <path d="M-12 -106 L-13.5 -20 M12 -106 L13.5 -20" stroke={SKIN} strokeWidth="16" strokeLinecap="round" />
      <path d="M-13.5 -42 L-13.5 -14 M13.5 -42 L13.5 -14" stroke="#fffaf3" strokeWidth="17" strokeLinecap="round" />
      <path d="M-21.5 -35 h16 M5.5 -35 h16" stroke="#9db7d6" strokeWidth="2.4" />
      {[-1, 1].map((s) => (
        <g key={s} transform={`translate(${s * 2} 0) scale(${-s} 1)`}>
          {back ? (
            <path d="M-14.5 -15 C-22 -15 -26 -10 -26 -5 C-26 -1.5 -24 0 -21 0 H-8 C-5 0 -3 -1.5 -3 -5 C-3 -10 -7 -15 -14.5 -15Z" fill="url(#tkh-shoe-navy)" />
          ) : (
            <>
              <path d="M-14.5 -17 C-24 -17 -30 -10 -30 -5 C-30 -1.5 -28 0 -24 0 H-5 C-1.5 0 0.5 -1.5 0.5 -5 C0.5 -10 -5 -17 -14.5 -17Z" fill="url(#tkh-shoe-navy)" />
              <path d="M-23 -12 Q-14.5 -8.5 -6 -12" fill="none" stroke="#cfa86f" strokeWidth="1.6" strokeLinecap="round" />
              <ellipse cx="-21" cy="-12" rx="3" ry="1.3" fill="#fff" opacity="0.25" />
            </>
          )}
          <path d={back ? "M-26 -1.8 H-3" : "M-30 -2 H0.5"} stroke="#efe4d2" strokeWidth="3" />
        </g>
      ))}
    </>
  );
}

const BOY_TORSO = "M-34 -264 C-37 -232 -33 -200 -30 -174 H30 C33 -200 37 -232 34 -264 C19 -272 -19 -272 -34 -264Z";
const BOY_SHORTS = "M-31 -180 H31 L35 -112 H3 L0 -130 L-3 -112 H-35 Z";

function BoySleeve() {
  return (
    <>
      <path d="M-11 -3 C-11 -10 9 -10 13 -2 L14.5 21 L-10 22.5 Z" fill="url(#tkh-ivory)" />
      <path d="M-11 -3 C-11 -10 9 -10 13 -2 L14.5 21 L-10 22.5 Z" fill="url(#tkh-knit)" opacity="0.5" />
      <path d="M-10 19.6 L14.5 18.2" stroke="#1c2d52" strokeWidth="1.6" />
      <path d="M-10 22.2 L14.5 20.8" stroke="#e5d8c2" strokeWidth="1.4" />
    </>
  );
}

function BoyShorts({ back = false }: { back?: boolean }) {
  return (
    <>
      <path d={BOY_SHORTS} fill="url(#tkh-navy)" />
      <path d="M-35 -118 H-3 M3 -118 H35" stroke="#14213e" strokeWidth="3.6" />
      <path d="M-18 -160 L-19 -118 M18 -160 L19 -118" stroke="#3d5590" strokeWidth="1.1" opacity="0.6" />
      {back ? (
        <path d="M-24 -166 h14 v10 h-14z M10 -166 h14 v10 h-14z" fill="none" stroke="#14213e" strokeWidth="1.4" />
      ) : (
        <>
          <path d="M-23 -177 Q-29 -165 -31 -152 M23 -177 Q29 -165 31 -152" fill="none" stroke="#14213e" strokeWidth="1.5" strokeLinecap="round" />
          <path d="M0 -177 V-136" stroke="#14213e" strokeWidth="1" opacity="0.6" />
        </>
      )}
      {/* Dusty-rose woven belt with a gold buckle */}
      <rect x="-31.5" y="-184" width="63" height="8" rx="2" fill="#c98e98" />
      <path d="M-31 -180 H31" stroke="#b77985" strokeWidth="0.8" strokeDasharray="2 1.6" />
      <path d="M-21 -185 v10 M21 -185 v10" stroke="#1c2d52" strokeWidth="3" />
      {!back && <rect x="-5.5" y="-185.5" width="11" height="11" rx="2" fill="none" stroke="url(#tkh-gold)" strokeWidth="2.2" />}
    </>
  );
}

function BoyFront({ headRef }: { headRef: Ref<SVGGElement> }) {
  return (
    <>
      <g className={styles.body}>
        <BoyLegs />
        <path d="M-8.5 -284 h17 v22 q-8.5 5 -17 0z" fill={SKIN_SHADE} />
        {/* Ivory knit polo */}
        <path d={BOY_TORSO} fill="url(#tkh-ivory)" />
        <path d={BOY_TORSO} fill="url(#tkh-knit)" opacity="0.5" />
        <rect x="-4.5" y="-262" width="9" height="30" rx="2" fill="none" stroke="#dccdb4" strokeWidth="1.2" />
        <g fill="url(#tkh-gold)">
          <circle cx="0" cy="-255" r="1.8" />
          <circle cx="0" cy="-246" r="1.8" />
          <circle cx="0" cy="-237" r="1.8" />
        </g>
        <path d="M-18 -243 l1.2 2.6 2.8 0.3 -2.1 1.9 0.6 2.8 -2.5 -1.4 -2.5 1.4 0.6 -2.8 -2.1 -1.9 2.8 -0.3z" fill="url(#tkh-gold)" />
        <BoyShorts />
        {/* Arms: the boy presents with his outer (right on screen) hand */}
        <Arm x={33} y={-260} side={1} upper={42} fore={35} width={13} role="lead" sleeve={<BoySleeve />} />
        <Arm x={-33} y={-260} side={-1} upper={42} fore={35} width={13} role="support" sleeve={<BoySleeve />} />
        {/* Polo collar with navy tipping */}
        <path d="M-2 -267 L-6 -251 L-20 -259 C-16 -266 -9 -268 -2 -267Z M2 -267 L6 -251 L20 -259 C16 -266 9 -268 2 -267Z" fill="url(#tkh-ivory)" />
        <path d="M-6 -251 L-20 -259 M6 -251 L20 -259" stroke="#1c2d52" strokeWidth="1.6" strokeLinecap="round" />
      </g>

      <g ref={headRef} className={`${styles.head} ${styles.boyHead}`}>
        <g transform="translate(0 -314)">
          <path d="M-37 2 C-39 -35 -21 -51 2 -51 C27 -51 41 -33 37 4 L34 14 H-34 Z" fill="url(#tkh-hair-boy)" />
          <ellipse cx="-34.5" cy="4" rx="6" ry="8" fill={SKIN_SHADE} />
          <ellipse cx="34.5" cy="4" rx="6" ry="8" fill={SKIN_SHADE} />
          <path d={FACE} fill="url(#tkh-face)" />
          <g className={styles.features}>
            <path d="M-20 -12.5 q6.5 -4 13 -1 M7 -13.5 q6.5 -3 13 1" fill="none" stroke="#3b2a20" strokeWidth="2.6" strokeLinecap="round" />
            <Eye id="tkh-eye-bl" x={-12.5} />
            <Eye id="tkh-eye-br" x={12.5} />
            <path d="M-2.2 8.6 q2.2 2.4 4.4 0" fill="none" stroke={SKIN_LINE} strokeWidth="1.6" strokeLinecap="round" />
            <path d="M-10 15 Q0 27 10 15 Q0 20 -10 15Z" fill="#c95d6f" />
            <path d="M-6.4 17 Q0 20 6.4 17" fill="none" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" />
            <ellipse cx="-21" cy="12" rx="6.5" ry="4.6" fill="#f29aa8" opacity="0.32" />
            <ellipse cx="21" cy="12" rx="6.5" ry="4.6" fill="#f29aa8" opacity="0.32" />
          </g>
          <g className={styles.hairFront}>
            <path
              d="M-36 -2 C-39 -31 -22 -50 4 -50 C26 -50 40 -37 36 -6 C32 -19 25 -26 16 -28 C19 -22 17 -18 12 -21 C3 -27 -11 -25 -21 -20 C-29 -16 -33 -9 -36 -2Z"
              fill="url(#tkh-hair-boy)"
            />
            <path d="M-14 -41 q13 -8 28 -2 M-24 -30 q10 -8 22 -8 M18 -36 q8 4 12 14" fill="none" stroke="#7a573f" strokeWidth="1.5" strokeLinecap="round" opacity="0.6" />
          </g>
        </g>
      </g>
    </>
  );
}

function BoyBack() {
  return (
    <>
      <g className={styles.body}>
        <BoyLegs back />
        <path d="M-8.5 -284 h17 v22 q-8.5 5 -17 0z" fill={SKIN_SHADE} />
        <path d={BOY_TORSO} fill="url(#tkh-ivory)" />
        <path d={BOY_TORSO} fill="url(#tkh-knit)" opacity="0.5" />
        <BoyShorts back />
        <Arm x={33} y={-260} side={1} upper={42} fore={35} width={13} role="still" sleeve={<BoySleeve />} />
        <Arm x={-33} y={-260} side={-1} upper={42} fore={35} width={13} role="still" sleeve={<BoySleeve />} />
        <path d="M-20 -262 Q0 -270 20 -262 L19 -256 Q0 -263 -19 -256Z" fill="url(#tkh-ivory)" />
        <path d="M-19 -256 Q0 -263 19 -256" fill="none" stroke="#1c2d52" strokeWidth="1.6" />
      </g>
      <g transform="translate(0 -314)">
        <path d="M-37 4 C-39 -35 -21 -52 2 -52 C27 -52 41 -34 37 6 C36 16 30 22 22 24 C10 26 -10 26 -22 24 C-30 22 -36 16 -37 4Z" fill="url(#tkh-hair-boy)" />
        <path d="M-22 -36 Q-10 -20 -12 16 M0 -44 Q4 -18 2 20 M20 -36 Q12 -14 14 16" fill="none" stroke="#7a573f" strokeWidth="1.3" opacity="0.45" />
        <path d="M-14 22 q3 4 6 0 q3 4 6 0 q3 4 6 0 q3 4 6 0" fill="none" stroke="#33241a" strokeWidth="1.4" opacity="0.6" />
      </g>
    </>
  );
}

export function Boy({ transform, gesture, rest, className, rootRef, frontRef, backRef, headRef }: FigureProps) {
  return (
    <g ref={rootRef} transform={transform} style={restStyle(rest)} data-gesture={gesture} className={className}>
      <ellipse cx="0" cy="1" rx="38" ry="7.5" fill="url(#tkh-contact)" />
      <g ref={frontRef}>
        <BoyFront headRef={headRef} />
      </g>
      <g ref={backRef} opacity="0">
        <BoyBack />
      </g>
    </g>
  );
}
