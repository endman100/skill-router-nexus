import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {colors, fonts} from '../design/tokens';

// Source calibration: V00 framework cards at 00:01:49–00:01:55; values are segment-local.

export type FrameworkCardProps = {
  label: string;
  title: string;
  accent: string;
  delay?: number;
  initiallyVisible?: boolean;
};

export const FrameworkCard: React.FC<FrameworkCardProps> = ({
  label,
  title,
  accent,
  delay = 0,
  initiallyVisible = false,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const entrance = initiallyVisible
    ? 1
    : spring({
        frame: frame - delay,
        fps,
        durationInFrames: 28,
        config: {damping: 20, stiffness: 200},
      });

  return (
    <div
      style={{
        position: 'relative',
        width: 545,
        height: 240,
        boxSizing: 'border-box',
        padding: '51px 40px',
        borderRadius: 20,
        border: '2px solid rgba(255,255,255,0.075)',
        background: `linear-gradient(145deg, ${colors.panel} 0%, #272727 100%)`,
        boxShadow: `0 15px 44px ${accent}12, inset 0 1px 0 rgba(255,255,255,0.02)`,
        opacity: entrance,
        transform: `translateY(${(1 - entrance) * 28}px) scale(${0.965 + entrance * 0.035})`,
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          width: 290,
          height: 180,
          left: -120,
          bottom: -125,
          background: `radial-gradient(circle, ${accent}18 0%, transparent 68%)`,
        }}
      />
      <div
        style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          gap: 15,
          color: '#d1d1d1',
          fontFamily: fonts.sans,
          fontSize: 28,
          fontWeight: 700,
          lineHeight: 1,
        }}
      >
        <span
          style={{
            width: 19,
            height: 19,
            flex: '0 0 auto',
            borderRadius: '50%',
            backgroundColor: accent,
            boxShadow: `0 0 14px ${accent}55`,
          }}
        />
        {label}
      </div>
      <div
        style={{
          position: 'relative',
          marginTop: 29,
          color: colors.text,
          fontFamily: fonts.mono,
          fontSize: 43,
          fontWeight: 700,
          lineHeight: 1,
          letterSpacing: -2,
          whiteSpace: 'nowrap',
        }}
      >
        {title}
      </div>
      <div
        style={{
          position: 'relative',
          marginTop: 31,
          width: 88,
          height: 5,
          borderRadius: 3,
          backgroundColor: accent,
          boxShadow: `0 0 14px ${accent}45`,
        }}
      />
    </div>
  );
};
