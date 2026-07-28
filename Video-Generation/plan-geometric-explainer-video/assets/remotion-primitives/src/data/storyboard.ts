import {colors} from '../design/tokens';

export const FPS = 60;
export const DURATION_IN_FRAMES = 27 * FPS;

export const frameworks = [
  {label: '人氣框架', title: 'Get Shit Done', accent: colors.orange},
  {label: '人氣框架', title: 'Spec-Kit', accent: colors.purple},
  {label: '人氣框架', title: 'Superpowers', accent: colors.green},
] as const;

export const steps = Array.from({length: 9}, (_, index) => index + 1);

export type CaptionCue = {
  start: number;
  end: number;
  text: string;
};

// Original subtitle times are shifted so 00:01:49.000 becomes t=0.
export const captions: CaptionCue[] = [
  {start: 0, end: 0.279, text: '像是 Get Shit Done，Spec-Kit 或 Superpowers'},
  {start: 0.639, end: 2.319, text: '但 Matt 覺得這些大框架的毛病'},
  {start: 2.44, end: 5.419, text: '在於它們想把你整個開發流程接管過去'},
  {start: 5.739, end: 6.319, text: '什麼意思？'},
  {start: 6.76, end: 10.15, text: '以 Spec-Kit 來說，它會把從寫規格、做計畫到實作'},
  {start: 10.15, end: 11.85, text: '全綁成一條又重又硬的固定流程'},
  {start: 11.85, end: 13.55, text: '只要你前面一步定歪了'},
  {start: 13.55, end: 15.85, text: '錯誤就會順著整條線傳染到後面'},
  {start: 15.85, end: 17.85, text: '等你想改，往往整條都得重跑'},
  {start: 17.85, end: 18.8, text: '特別難救'},
  {start: 19.08, end: 21.18, text: '所以他的 skill 走完全相反的路'},
  {start: 21.18, end: 24, text: '每一個都刻意做得很小，很好改，還能自由拼裝'},
  {start: 24.339, end: 26.179, text: '這個小，而且模組化的理念'},
  {start: 26.179, end: 27, text: '就是他後面所有東西的底層邏輯'},
];

export const sceneFrames = {
  cards: {from: 0, duration: 90},
  pipeline: {from: 150, duration: 1020},
  modules: {from: 1120, duration: 500},
} as const;
