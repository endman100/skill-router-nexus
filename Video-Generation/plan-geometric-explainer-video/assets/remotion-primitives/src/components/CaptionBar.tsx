import {Sequence, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {captions, type CaptionCue} from '../data/storyboard';
import {colors, fonts, layout} from '../design/tokens';

// Source calibration: V00 bottom caption track; exact 27 s replica covers 00:01:49–00:02:16.

const CaptionBar: React.FC<{
  cue: CaptionCue;
  durationInFrames: number;
  instant?: boolean;
}> = ({cue, durationInFrames, instant = false}) => {
  const frame = useCurrentFrame();
  const fadeFrames = instant ? 0 : 4;
  const fadeIn = fadeFrames === 0 ? 1 : interpolate(frame, [0, fadeFrames], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        bottom: layout.captionBottom,
        transform: 'translateX(-50%)',
        minHeight: 98,
        maxWidth: 1660,
        padding: '0 58px 3px',
        borderRadius: 10,
        backgroundColor: colors.black,
        color: colors.text,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        whiteSpace: 'nowrap',
        fontFamily: fonts.sans,
        fontSize: 42,
        lineHeight: 1,
        fontWeight: 900,
        letterSpacing: -0.45,
        opacity: fadeIn,
        textShadow: '0 2px 0 rgba(255,255,255,0.04)',
      }}
    >
      {cue.text}
    </div>
  );
};

export const CaptionTrack: React.FC = () => {
  const {fps} = useVideoConfig();

  return (
    <>
      {captions.map((cue, index) => {
        const from = Math.max(0, Math.round(cue.start * fps));
        const durationInFrames = Math.max(1, Math.round((cue.end - Math.max(0, cue.start)) * fps));
        return (
          <Sequence
            key={`${cue.start}-${cue.text}`}
            from={from}
            durationInFrames={durationInFrames}
            premountFor={fps}
          >
            <CaptionBar cue={cue} durationInFrames={durationInFrames} instant={index === 0} />
          </Sequence>
        );
      })}
    </>
  );
};
