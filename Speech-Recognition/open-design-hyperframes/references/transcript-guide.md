# Transcript Guide

## How Transcripts Are Generated

Use `hyperframes transcribe` only to import or normalize an existing transcript:

```bash
# Import an existing transcript from another tool
npx hyperframes transcribe captions.srt
npx hyperframes transcribe captions.vtt
npx hyperframes transcribe openai-response.json
```

## Supported Input Formats

The CLI auto-detects and normalizes these formats:

| Format                | Extension | Source                                                                      | Word-level?       |
| --------------------- | --------- | --------------------------------------------------------------------------- | ----------------- |
| Legacy word JSON      | `.json`   | Existing external artifact; do not create it through this skill             | Yes               |
| Router result JSON    | `.json`   | `asr-router` normalized output                                               | Yes               |
| SRT subtitles         | `.srt`    | Video editors, subtitle tools, YouTube                                      | No (phrase-level) |
| VTT subtitles         | `.vtt`    | Web players, YouTube, transcription services                                | No (phrase-level) |
| Normalized word array | `.json`   | Pre-processed by any tool                                                   | Yes               |

**Word-level timestamps produce better captions.** SRT/VTT give phrase-level timing, which works but can't do per-word animation effects.

## ASR source

When audio must be recognized, invoke `Speech-Recognition/asr-router` with
`profile=word_timestamps`, then import its normalized result. Model selection,
language behavior, credentials, endpoints, and fallback rules live only in the
Router schema and the selected provider guide.

## Transcript Quality Check (Mandatory)

After every transcription, **read the transcript and check for quality issues before proceeding.** Bad transcripts produce nonsensical captions. Never skip this step.

### What to look for

| Signal                       | Example                                | Cause                                                                        |
| ---------------------------- | -------------------------------------- | ---------------------------------------------------------------------------- |
| Music note tokens (`♪`, `�`) | `{ "text": "♪" }` or `{ "text": "�" }` | Whisper detected music, not speech                                           |
| Garbled / nonsense words     | "Do a chin", "Get so gay", "huh"       | Model misheard lyrics or background noise                                    |
| Long gaps with no words      | 20+ seconds of only `♪` tokens         | Instrumental section — expected, but high ratio means speech is being missed |
| Repeated filler              | Many "huh", "uh", "oh" entries         | Model is hallucinating on music                                              |
| Very short word spans        | Words with `end - start < 0.05`        | Unreliable timestamp alignment                                               |

### Automatic retry rules

**If more than 20% of entries are `♪`/`�` tokens, or the transcript contains obvious nonsense words, the transcription failed.** Do not proceed with the bad transcript. Instead:

1. If fallback is allowed, return the failed quality signal to ASR Router and
   let it select the next eligible provider.
2. If all eligible providers fail, tell the user the audio is too noisy and
   suggest providing an approved transcript or lyrics manually.
3. **Always clean the transcript** before building captions — filter out `♪`/`�` tokens and entries where `text` is a single non-word character. Only real words should reach the caption composition.

### Cleaning a transcript

After transcription (even with a good model), strip non-word entries:

```js
var raw = JSON.parse(transcriptJson);
var words = raw.filter(function (w) {
  if (!w.text || w.text.trim().length === 0) return false;
  if (/^[♪�\u266a\u266b\u266c\u266d\u266e\u266f]+$/.test(w.text)) return false;
  if (/^(huh|uh|um|ah|oh)$/i.test(w.text) && w.end - w.start < 0.1) return false;
  return true;
});
```

## If No Transcript Exists

1. Check the project root for `transcript.json`, `.srt`, or `.vtt` files
2. If none exists, invoke ASR Router with `profile=word_timestamps` and import
   the normalized result.
3. **Read the transcript and run the quality check** (see above). If it fails,
   let Router follow its configured fallback policy or suggest manual lyrics.
