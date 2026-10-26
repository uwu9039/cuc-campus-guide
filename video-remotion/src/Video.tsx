import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import beats from "./beats.json";

const INK = "#15130f";
const PAPER = "#f6f2e9";
const MUTED = "#bdb5a4";
const SEAL = "#e0483a";
const FPS = 30;

type Beat = {
  id: string;
  kind: "punch" | "shot" | "stat";
  text: string;
  head?: string;
  sub?: string;
  line?: string;
  img?: string;
  zoom?: number;
  num?: string;
  label?: string;
  note?: string;
  audio: string;
  dur: number;
  trans?: string;
};

const TIMELINE = (() => {
  let t = 0;
  return (beats as Beat[]).map((b) => {
    const start = t;
    const frames = Math.round(b.dur * FPS);
    t += frames;
    return { ...b, start, frames };
  });
})();

export const TOTAL_FRAMES = TIMELINE.reduce((a, b) => a + b.frames, 0);

/** 快节奏入场：弹簧更硬，十几帧就位 */
const snap = (frame: number, fps: number, delay = 0) =>
  spring({
    frame: frame - delay,
    fps,
    config: { damping: 26, stiffness: 190, mass: 0.5 },
    durationInFrames: 18,
  });

const Backdrop: React.FC = () => {
  const frame = useCurrentFrame();
  const drift = (frame % 300) / 300;
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(1200px 760px at ${18 + drift * 10}% 32%, #262219 0%, ${INK} 64%)`,
      }}
    />
  );
};

/**
 * 转场：每拍入场按类型做不同花样
 *   whip  鞭甩：横向冲入 + 运动模糊
 *   zoom  推镜：从放大收进 + 去模糊
 *   flash 白闪：切点闪一下白光
 *   skew  斜切：斜角擦除推入
 *   shake 震屏：落地抖一下
 */
const Transition: React.FC<{ children: React.ReactNode; type: string }> = ({ children, type }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame, fps, config: { damping: 26, stiffness: 260, mass: 0.4 }, durationInFrames: 11 });

  let style: React.CSSProperties = {};
  if (type === "whip") {
    style = {
      transform: `translateX(${(1 - p) * 460}px) skewX(${(1 - p) * -8}deg)`,
      filter: `blur(${(1 - p) * 16}px)`,
    };
  } else if (type === "zoom") {
    style = {
      transform: `scale(${1 + (1 - p) * 0.4})`,
      filter: `blur(${(1 - p) * 20}px)`,
    };
  } else if (type === "flash") {
    style = { transform: `scale(${1 + (1 - p) * 0.06})` };
  } else if (type === "skew") {
    style = {
      clipPath: `polygon(0 0, ${100 * p}% 0, ${100 * p - 18}% 100%, 0 100%)`,
      transform: `translateX(${(1 - p) * 90}px)`,
    };
  } else if (type === "shake") {
    const decay = Math.max(0, 1 - frame / 12);
    const jx = Math.sin(frame * 2.4) * 16 * decay;
    const jy = Math.cos(frame * 3.1) * 10 * decay;
    style = { transform: `translate(${jx}px, ${jy}px) scale(${1 + decay * 0.02})` };
  }

  return (
    <AbsoluteFill style={style}>
      {children}
      {type === "flash" && (
        <AbsoluteFill
          style={{
            background: "#fff",
            opacity: interpolate(frame, [0, 2, 9], [0.92, 0.55, 0], { extrapolateRight: "clamp" }),
            pointerEvents: "none",
          }}
        />
      )}
    </AbsoluteFill>
  );
};


const Punch: React.FC<{ b: Beat }> = ({ b }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = snap(frame, fps, 0);
  const c = snap(frame, fps, 5);

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          fontSize: 190,
          fontWeight: 800,
          color: PAPER,
          letterSpacing: "-0.04em",
          lineHeight: 1,
          transform: `translateY(${(1 - a) * 26}px) scale(${0.97 + a * 0.03})`,
        }}
      >
        {b.head}
      </div>
      <div
        style={{
          marginTop: 26,
          fontSize: 64,
          fontWeight: 700,
          color: SEAL,
          transform: `translateY(${(1 - c) * 16}px)`,
        }}
      >
        {b.sub}
      </div>
    </AbsoluteFill>
  );
};

const Shot: React.FC<{ b: Beat }> = ({ b }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const head = snap(frame, fps, 0);
  const line = snap(frame, fps, 4);
  const card = snap(frame, fps, 2);

  const z = b.zoom ?? 1;
  const frames = Math.round(b.dur * FPS);
  const drift = interpolate(frame, [0, frames], [0, 1]);
  const scale = z + drift * 0.02 * z;
  // 放大时把视点移到答案区域，避免只放大到页头
  const origin = z > 1.15 ? "58% 42%" : "50% 50%";

  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 116, top: 380, width: 650 }}>
        <div
          style={{
            fontSize: 56,
            lineHeight: 1.24,
            fontWeight: 800,
            color: PAPER,
            letterSpacing: "-0.02em",
            transform: `translateY(${(1 - head) * 18}px)`,
          }}
        >
          {b.head}
        </div>
        <div style={{ marginTop: 18, fontSize: 25, lineHeight: 1.6, color: MUTED }}>
          {b.line}
        </div>
        <div style={{ width: 96, height: 5, background: SEAL, marginTop: 26 }} />
      </div>

      <div
        style={{
          position: "absolute",
          left: 800,
          top: 130,
          width: 1000,
          height: 820,
          overflow: "hidden",
          borderRadius: 6,
          border: "1px solid #3a352c",
          boxShadow: "0 44px 100px -34px rgba(0,0,0,.9)",
          transform: `translateY(${(1 - card) * 34}px)`,
        }}
      >
        <Img
          src={staticFile(b.img!)}
          style={{ width: "100%", display: "block", transform: `scale(${scale})`, transformOrigin: origin }}
        />
      </div>
    </AbsoluteFill>
  );
};

const Stat: React.FC<{ b: Beat }> = ({ b }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const target = Number(b.num ?? 0);
  const count = Math.round(interpolate(frame, [0, 26], [0, target], { extrapolateRight: "clamp" }));
  const a = snap(frame, fps, 0);
  const n = snap(frame, fps, 10);

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          fontSize: 300,
          fontWeight: 800,
          color: PAPER,
          letterSpacing: "-0.05em",
          lineHeight: 1,
          transform: `scale(${0.96 + a * 0.04})`,
        }}
      >
        {count}
      </div>
      <div style={{ fontSize: 52, color: SEAL, fontWeight: 700, marginTop: 8 }}>{b.label}</div>
      <div style={{ fontSize: 26, color: MUTED, marginTop: 18 }}>{b.note}</div>
    </AbsoluteFill>
  );
};

const Progress: React.FC = () => {
  const frame = useCurrentFrame();
  const p = frame / TOTAL_FRAMES;
  return (
    <div style={{ position: "absolute", left: 0, bottom: 0, width: `${p * 100}%`, height: 5, background: SEAL, opacity: 0.85 }} />
  );
};

export const CampusGuide: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: INK }}>
    {TIMELINE.map((b) => (
      <Sequence key={b.id} from={b.start} durationInFrames={b.frames} name={b.id}>
        <Audio src={staticFile(b.audio)} />
        <Backdrop />
        <Transition type={b.trans ?? "whip"}>
          {b.kind === "punch" ? <Punch b={b} /> : b.kind === "stat" ? <Stat b={b} /> : <Shot b={b} />}
        </Transition>
      </Sequence>
    ))}
    <Progress />
  </AbsoluteFill>
);
