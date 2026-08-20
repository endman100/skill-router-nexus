#!/usr/bin/env node
/**
 * Check only AI剪口播's business dependencies.
 * ASR method availability and credentials are checked by the asr-router skill.
 */

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const SKILL_DIR = path.resolve(__dirname, '..');
const SENTINEL = path.join(SKILL_DIR, '.setup_done');

function commandExists(command, args) {
  return spawnSync(command, args, { stdio: 'ignore' }).status === 0;
}

const dependencies = [
  ['ffmpeg', ['-version']],
  ['node', ['--version']],
];
let ready = true;
for (const [command, args] of dependencies) {
  const ok = commandExists(command, args);
  console.log(`${ok ? '✓' : '✗'} ${command}`);
  ready = ready && ok;
}

console.log('i ASR 可用性、模型与 API 凭证由 Agent 调用 asr-router 时检查');
if (ready) {
  fs.writeFileSync(SENTINEL, new Date().toISOString() + '\n');
  console.log('✓ AI剪口播业务依赖已就绪');
  process.exit(0);
}
console.log('✗ 请先修复以上业务依赖');
process.exit(1);
