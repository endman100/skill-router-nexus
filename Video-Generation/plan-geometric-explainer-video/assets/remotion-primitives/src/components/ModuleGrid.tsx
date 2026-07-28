import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {colors, fonts} from '../design/tokens';

// Source calibration: V00 scattered tiles converge at 00:02:07.80–00:02:10.20; values are segment-local.

const modules = [
  {column: 0, row: 0, accent: colors.orange, offsetX: 240, offsetY: 300, rotate: -18},
  {column: 1, row: 0, accent: colors.purple, offsetX: 25, offsetY: 300, rotate: 20},
  {column: 2, row: 0, accent: colors.green, offsetX: -90, offsetY: 300, rotate: -24},
  {column: 0, row: 1, accent: colors.orange, offsetX: -95, offsetY: -45, rotate: 17},
  {column: 1, row: 1, accent: colors.purple, offsetX: 10, offsetY: -45, rotate: -16},
  {column: 2, row: 1, accent: colors.green, offsetX: 70, offsetY: -45, rotate: 21},
] as const;

const labels = [
  {text: '小', accent: colors.orange, left: 652, width: 128, revealAt: 1250},
  {text: '好改', accent: colors.purple, left: 810, width: 167, revealAt: 1270},
  {text: '自由拼裝', accent: colors.green, left: 1007, width: 229, revealAt: 1296},
] as const;

export const ModuleGrid: React.FC<{timelineOffset: number}> = ({timelineOffset}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const absoluteFrame = frame + timelineOffset;
  const converge = spring({
    frame: absoluteFrame - 1170,
    fps,
    durationInFrames: 90,
    config: {damping: 18, stiffness: 150},
  });
  const formulaReveal = spring({
    frame: absoluteFrame - 1440,
    fps,
    durationInFrames: 30,
    config: {damping: 200},
  });

  return (
    <div style={{position: 'absolute', inset: 0}}>
      {labels.map((label) => {
        const reveal = spring({
          frame: absoluteFrame - label.revealAt,
          fps,
          durationInFrames: 24,
          config: {damping: 20, stiffness: 200},
        });
        return (
          <div
            key={label.text}
            style={{
              position: 'absolute',
              top: 121,
              left: label.left,
              width: label.width,
              height: 101,
              borderRadius: 52,
              border: `2px solid ${label.accent}`,
              boxSizing: 'border-box',
              color: colors.text,
              backgroundColor: `${label.accent}0d`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontFamily: fonts.sans,
              fontSize: label.text.length > 3 ? 35 : 38,
              fontWeight: 900,
              opacity: reveal,
              transform: `translateY(${(1 - reveal) * 19}px) scale(${0.94 + reveal * 0.06})`,
              boxShadow: `0 0 22px ${label.accent}12`,
            }}
          >
            {label.text}
          </div>
        );
      })}

      {modules.map((module, index) => {
        const targetX = 786 + module.column * 121;
        const targetY = 337 + module.row * 166;
        const x = targetX + module.offsetX * (1 - converge);
        const y = targetY + module.offsetY * (1 - converge);
        const rotation = module.rotate * (1 - converge);
        const heightProgress = interpolate(absoluteFrame, [1210, 1260], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        const moduleHeight = 107 + heightProgress * 47;
        const opacity = interpolate(absoluteFrame, [1160 + index * 5, 1190 + index * 5], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });

        return (
          <div
            key={`${module.column}-${module.row}`}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: 107,
              height: moduleHeight,
              borderRadius: 17,
              border: `3px solid ${module.accent}`,
              boxSizing: 'border-box',
              backgroundColor: `${module.accent}13`,
              boxShadow: `0 0 25px ${module.accent}2c`,
              transform: `rotate(${rotation}deg) scale(${0.9 + converge * 0.1})`,
              opacity,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 16,
            }}
          >
            {[0, 1].map((dot) => (
              <div
                key={dot}
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: '50%',
                  backgroundColor: module.accent,
                  opacity: 0.62,
                  boxShadow: `0 0 10px ${module.accent}38`,
                }}
              />
            ))}
          </div>
        );
      })}

      <div
        style={{
          position: 'absolute',
          top: 765,
          left: '50%',
          transform: `translateX(-50%) translateY(${(1 - formulaReveal) * 16}px)`,
          display: 'flex',
          alignItems: 'center',
          gap: 23,
          width: 817,
          height: 113,
          boxSizing: 'border-box',
          padding: '0 36px',
          borderLeft: `4px solid ${colors.orange}`,
          background: 'linear-gradient(90deg, rgba(45,45,45,0.96), rgba(39,39,39,0.72))',
          color: '#bdbdbd',
          fontFamily: fonts.sans,
          fontSize: 36,
          fontWeight: 700,
          opacity: formulaReveal,
          whiteSpace: 'nowrap',
        }}
      >
        <span>小 × 模組化</span>
        <span style={{color: colors.dim}}>＝</span>
        <span style={{color: colors.orange}}>一切設計的底層邏輯</span>
      </div>
    </div>
  );
};
