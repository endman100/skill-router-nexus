import {
  interpolate,
  interpolateColors,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {steps} from '../data/storyboard';
import {colors, fonts} from '../design/tokens';

const NODE_WIDTH = 118;
const NODE_HEIGHT = 118;
const NODE_GAP = 82;
const NODE_LEFT = 100;
const NODE_TOP = 460;

const activationFrames = [390, 450, 465, 480, 510, 535, 558, 580, 600];

const errorFrameFor = (index: number) => {
  if (index === 0) return Number.POSITIVE_INFINITY;
  if (index === 1) return 780;
  return 822 + (index - 2) * 12;
};

const ErrorTag: React.FC<{absoluteFrame: number}> = ({absoluteFrame}) => {
  const {fps} = useVideoConfig();
  const reveal = spring({
    frame: absoluteFrame - 780,
    fps,
    durationInFrames: 24,
    config: {damping: 20, stiffness: 200},
  });

  return (
    <>
      <div
        style={{
          position: 'absolute',
          left: 253,
          top: 368,
          minWidth: 211,
          height: 61,
          padding: '0 19px',
          boxSizing: 'border-box',
          borderRadius: 31,
          border: `1px solid ${colors.red}66`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: colors.red,
          fontFamily: fonts.sans,
          fontSize: 27,
          fontWeight: 900,
          opacity: reveal,
          transform: `translateY(${(1 - reveal) * 13}px) scale(${0.96 + reveal * 0.04})`,
        }}
      >
        步驟發生偏差
      </div>
      <div
        style={{
          position: 'absolute',
          left: 337,
          top: 437,
          width: 0,
          height: 0,
          borderLeft: '22px solid transparent',
          borderRight: '22px solid transparent',
          borderBottom: '42px solid #ffd33d',
          opacity: reveal,
          filter: 'drop-shadow(0 4px 8px rgba(255,211,61,0.25))',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: 10,
            left: -3,
            width: 6,
            height: 17,
            borderRadius: 3,
            backgroundColor: '#2a2412',
          }}
        />
      </div>
    </>
  );
};

export const StepPipeline: React.FC<{timelineOffset: number}> = ({timelineOffset}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const absoluteFrame = frame + timelineOffset;

  const finalTag = spring({
    frame: absoluteFrame - 930,
    fps,
    durationInFrames: 26,
    config: {damping: 200},
  });
  const chainTag = spring({
    frame: absoluteFrame - 900,
    fps,
    durationInFrames: 25,
    config: {damping: 20, stiffness: 200},
  });

  return (
    <div style={{position: 'absolute', inset: 0}}>
      {steps.slice(0, -1).map((_, index) => {
        const nextActivation = activationFrames[index + 1];
        const activeProgress = interpolate(
          absoluteFrame,
          [nextActivation - 18, nextActivation],
          [0, 1],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
        );
        const connectorErrorFrame = index === 0 ? Number.POSITIVE_INFINITY : errorFrameFor(index + 1);
        const errorProgress = Number.isFinite(connectorErrorFrame)
          ? interpolate(absoluteFrame, [connectorErrorFrame, connectorErrorFrame + 12], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })
          : 0;
        const activeColor = interpolateColors(activeProgress, [0, 1], ['#3d3d3d', colors.orange]);
        const connectorColor = interpolateColors(errorProgress, [0, 1], [activeColor, colors.red]);
        return (
          <div
            key={`connector-${index}`}
            style={{
              position: 'absolute',
              left: NODE_LEFT + NODE_WIDTH + index * (NODE_WIDTH + NODE_GAP),
              top: NODE_TOP + NODE_HEIGHT / 2 - 2,
              width: NODE_GAP,
              height: 4,
              backgroundColor: connectorColor,
              boxShadow: activeProgress > 0.01 ? `0 0 12px ${connectorColor}50` : 'none',
            }}
          />
        );
      })}

      {steps.map((number, index) => {
        const activeProgress = interpolate(
          absoluteFrame,
          [activationFrames[index] - 18, activationFrames[index]],
          [0, 1],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
        );
        const errorFrame = errorFrameFor(index);
        const errorProgress = Number.isFinite(errorFrame)
          ? interpolate(absoluteFrame, [errorFrame, errorFrame + 12], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })
          : 0;
        const activeBorder = interpolateColors(activeProgress, [0, 1], [colors.border, colors.orange]);
        const borderColor = interpolateColors(errorProgress, [0, 1], [activeBorder, colors.red]);
        const activeBackground = interpolateColors(activeProgress, [0, 1], [colors.panel, '#342a16']);
        const backgroundColor = interpolateColors(errorProgress, [0, 1], [activeBackground, '#3c171a']);
        const textColor = interpolateColors(errorProgress, [0, 1], [colors.text, colors.red]);
        const glowStrength = Math.max(activeProgress, errorProgress);

        return (
          <div
            key={number}
            style={{
              position: 'absolute',
              left: NODE_LEFT + index * (NODE_WIDTH + NODE_GAP),
              top: NODE_TOP,
              width: NODE_WIDTH,
              height: NODE_HEIGHT,
              borderRadius: 18,
              border: `3px solid ${borderColor}`,
              boxSizing: 'border-box',
              backgroundColor,
              color: textColor,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontFamily: fonts.mono,
              fontSize: 31,
              fontWeight: 700,
              boxShadow: glowStrength > 0.01 ? `0 0 23px ${borderColor}45` : 'none',
            }}
          >
            {number}
          </div>
        );
      })}

      {absoluteFrame >= 755 ? <ErrorTag absoluteFrame={absoluteFrame} /> : null}

      <div
        style={{
          position: 'absolute',
          top: 350,
          left: 812,
          width: 302,
          height: 76,
          boxSizing: 'border-box',
          borderRadius: 39,
          border: `1px solid ${colors.red}55`,
          backgroundColor: 'rgba(34,30,30,0.72)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 13,
          color: colors.red,
          fontFamily: fonts.sans,
          fontSize: 34,
          fontWeight: 900,
          opacity: chainTag,
          transform: `translateY(${(1 - chainTag) * 14}px) scale(${0.97 + chainTag * 0.03})`,
        }}
      >
        <span
          style={{
            width: 42,
            height: 42,
            borderRadius: 10,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#7e91a5',
            color: colors.text,
            fontFamily: fonts.mono,
            fontSize: 28,
          }}
        >
          ↻
        </span>
        <span>重新執行流程</span>
      </div>

      <div
        style={{
          position: 'absolute',
          top: 707,
          left: 744,
          width: 432,
          height: 100,
          borderRadius: 14,
          border: '1px solid rgba(246,162,26,0.16)',
          backgroundColor: 'rgba(43,40,34,0.76)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: colors.orange,
          fontFamily: fonts.sans,
          fontSize: 35,
          fontWeight: 900,
          opacity: finalTag,
          transform: `translateY(${(1 - finalTag) * 14}px)`,
        }}
      >
        及早修正，降低影響
      </div>
    </div>
  );
};
