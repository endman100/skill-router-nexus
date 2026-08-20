#!/usr/bin/env node
/**
 * 从 ASR Router normalized result 生成字级别字幕
 *
 * 用法: node generate_subtitles.js <asr-result.json> [delete_segments.json]
 * 输出: subtitles_words.json
 */

const fs = require('fs');
const path = require('path');

const resultFile = process.argv[2] || 'asr-result.json';
const deleteFile = process.argv[3];
const outDir = process.argv[4] || '.';

if (!fs.existsSync(resultFile)) {
  console.error('❌ 找不到文件:', resultFile);
  process.exit(1);
}

const result = JSON.parse(fs.readFileSync(resultFile, 'utf8'));

if (!result.schema_version || !Array.isArray(result.words)) {
  console.error('❌ 输入不是 ASR Router normalized result');
  console.error('响应顶层字段:', Object.keys(result));
  process.exit(1);
}

// 只消费 Router 契约中的真实 word；spacing 由本业务脚本重新计算。
const allWords = [];
for (const word of result.words) {
  const text = String(word.text || '').trim();
  const start = Number(word.start);
  const end = Number(word.end);
  if (word.type === 'spacing' || !text || !Number.isFinite(start) || !Number.isFinite(end)) continue;
  if (start < 0 || end < start) continue;
  allWords.push({ text, start, end });
}
if (allWords.length === 0) {
  console.error('❌ Router 结果没有可用的真实 word timestamps');
  process.exit(1);
}

console.log('原始字数:', allWords.length);

// 如果有删除片段，映射时间
let outputWords = allWords;

if (deleteFile && fs.existsSync(deleteFile)) {
  const deleteSegments = JSON.parse(fs.readFileSync(deleteFile, 'utf8'));
  console.log('删除片段数:', deleteSegments.length);

  function getDeletedTimeBefore(time) {
    let deleted = 0;
    for (const seg of deleteSegments) {
      if (seg.end <= time) {
        deleted += seg.end - seg.start;
      } else if (seg.start < time) {
        deleted += time - seg.start;
      }
    }
    return deleted;
  }

  function isDeleted(start, end) {
    for (const seg of deleteSegments) {
      if (start < seg.end && end > seg.start) return true;
    }
    return false;
  }

  outputWords = [];
  for (const word of allWords) {
    if (!isDeleted(word.start, word.end)) {
      const deletedBefore = getDeletedTimeBefore(word.start);
      outputWords.push({
        text: word.text,
        start: Math.round((word.start - deletedBefore) * 100) / 100,
        end: Math.round((word.end - deletedBefore) * 100) / 100
      });
    }
  }
  console.log('映射后字数:', outputWords.length);
}

// 添加空白标记（≥0.2秒才生成，与 gen_analysis.js 阈值一致）
const wordsWithGaps = [];
let lastEnd = 0;

for (const word of outputWords) {
  const gapDuration = word.start - lastEnd;

  if (gapDuration >= 0.2) {
    wordsWithGaps.push({
      text: '',
      start: Math.round(lastEnd * 100) / 100,
      end: Math.round(word.start * 100) / 100,
      isGap: true
    });
  }

  wordsWithGaps.push({
    text: word.text,
    start: word.start,
    end: word.end,
    isGap: false
  });
  lastEnd = word.end;
}

const gaps = wordsWithGaps.filter(w => w.isGap);
console.log('总元素数:', wordsWithGaps.length);
console.log('空白段数:', gaps.length);

fs.writeFileSync(path.join(outDir, 'subtitles_words.json'), JSON.stringify(wordsWithGaps, null, 2));
console.log(`✅ 已保存 ${path.join(outDir, 'subtitles_words.json')}`);
