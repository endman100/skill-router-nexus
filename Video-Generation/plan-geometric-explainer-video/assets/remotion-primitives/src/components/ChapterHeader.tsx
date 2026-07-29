import {colors, fonts} from '../design/tokens';

export const ChapterHeader: React.FC = () => {
  return (
    <>
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 4,
          display: 'flex',
          gap: 3,
          opacity: 0.72,
        }}
      >
        {Array.from({length: 6}, (_, index) => (
          <div
            key={index}
            style={{
              flex: 1,
              backgroundColor: index === 1 ? '#363636' : '#2a2a2a',
              borderRight: '1px solid #141414',
            }}
          />
        ))}
      </div>
      <div
        style={{
          position: 'absolute',
          top: 25,
          left: 42,
          height: 26,
          borderLeft: `3px solid ${colors.orange}`,
          display: 'flex',
          alignItems: 'center',
          paddingLeft: 13,
          gap: 11,
          fontFamily: fonts.sans,
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: 0.2,
        }}
      >
        <span style={{color: colors.orange}}>02 / 06</span>
        <span style={{color: '#adadad'}}>概念與流程</span>
      </div>
    </>
  );
};
