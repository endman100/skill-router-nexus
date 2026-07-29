import {colors} from '../design/tokens';

export const FPS = 60;
export const DURATION_IN_FRAMES = 27 * FPS;

export const frameworks = [
  {label: '概念模組', title: 'Input', accent: colors.orange},
  {label: '概念模組', title: 'Process', accent: colors.purple},
  {label: '概念模組', title: 'Output', accent: colors.green},
] as const;

export const steps = Array.from({length: 9}, (_, index) => index + 1);

export type CaptionCue = {
  start: number;
  end: number;
  text: string;
};

// Generic demo cues. Replace these with timestamps aligned to the final narration.
export const captions: CaptionCue[] = [
  {start: 0, end: 2.8, text: '先把一個抽象概念拆成可理解的模組'},
  {start: 3.1, end: 6.2, text: '再用固定結構呈現它們之間的關係'},
  {start: 6.6, end: 10.3, text: '流程先保持不動，接著依照敘述逐步啟用'},
  {start: 10.7, end: 14.4, text: '如果某一步出錯，錯誤狀態沿著連線向後傳遞'},
  {start: 14.8, end: 18.2, text: '相同的幾何結構讓前後狀態容易比較'},
  {start: 18.6, end: 22.5, text: '最後把元件整理成清楚、可替換、可組合的系統'},
  {start: 22.9, end: 27, text: '所有動畫都應由旁白中的語意時間點觸發'},
];

export const sceneFrames = {
  cards: {from: 0, duration: 90},
  pipeline: {from: 150, duration: 1020},
  modules: {from: 1120, duration: 500},
} as const;
