#!/usr/bin/env python3
"""Build local inference request data; never install, load, or call a model."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
POLICY = json.loads((BASE / 'references/model-policy.json').read_text(encoding='utf-8'))
MI_LANGUAGES = frozenset('Arabic|Azerbaijani|Bulgarian|Bengali|Catalan|Czech|Danish|German|Greek|English|Spanish|Persian|Finnish|French|Hebrew|Hindi|Croatian|Hungarian|Indonesian|Italian|Japanese|Kazakh|Khmer|Korean|Lao|Malay|Burmese|Norwegian|Dutch|Polish|Portuguese|Romanian|Russian|Slovak|Slovenian|Swedish|Tamil|Thai|Tagalog|Turkish|Urdu|Uzbek|Vietnamese|Cantonese|Chinese (Simplified)|Chinese (Traditional)'.split('|'))
HY_LANGUAGES = frozenset('Chinese|Traditional Chinese|English|French|Portuguese|Spanish|Japanese|Turkish|Russian|Arabic|Korean|Thai|Italian|German|Vietnamese|Malay|Indonesian|Filipino|Hindi|Polish|Czech|Dutch|Khmer|Burmese|Persian|Gujarati|Urdu|Telugu|Marathi|Hebrew|Bengali|Tamil|Ukrainian|Tibetan|Kazakh|Mongolian|Uyghur|Cantonese'.split('|'))
ALIASES = {
 'en':'English','ja':'Japanese','zh':'Chinese (Simplified)',
 'zh-cn':'Chinese (Simplified)','zh-hans':'Chinese (Simplified)',
 'zh-tw':'Chinese (Traditional)','zh-hant':'Chinese (Traditional)',
 'traditional chinese':'Chinese (Traditional)','simplified chinese':'Chinese (Simplified)',
 'chinese':'Chinese (Simplified)','ko':'Korean','fr':'French','de':'German',
 'es':'Spanish','pt':'Portuguese','ru':'Russian','ar':'Arabic','th':'Thai',
 'vi':'Vietnamese','id':'Indonesian','ms':'Malay','it':'Italian','hi':'Hindi',
 'yue':'Cantonese','tr':'Turkish','pl':'Polish','nl':'Dutch','uk':'Ukrainian',
 'bn':'Bengali','ta':'Tamil','fil':'Filipino','tl':'Tagalog',
 '繁體中文':'Chinese (Traditional)','简体中文':'Chinese (Simplified)',
 '簡體中文':'Chinese (Simplified)','英文':'English','日文':'Japanese',
}
INDEX_COMMON = frozenset('English|Japanese|Chinese (Simplified)|Chinese (Traditional)|Korean|French|German|Spanish|Portuguese|Russian|Arabic|Italian|Thai|Vietnamese|Indonesian'.split('|'))
INDEX_NAMES = {'English':'英语','Japanese':'日语','Chinese (Simplified)':'简体中文','Chinese (Traditional)':'繁体中文（台湾用语）','Korean':'韩语'}


def language_name(value: str) -> str:
    value = value.strip()
    if not value or any(c in value for c in '\r\n:<>'):
        raise ValueError('Invalid language name')
    if value.lower() == 'auto':
        return 'auto'
    if value.lower() in ALIASES:
        return ALIASES[value.lower()]
    known = MI_LANGUAGES | HY_LANGUAGES
    for name in known:
        if name.casefold() == value.casefold():
            return name
    return value


def candidates(profile: str = 'quality', model: str | None = None) -> list[str]:
    if model:
        if model not in POLICY['models']:
            raise ValueError('Unknown model alias: ' + model)
        return [model]  # Explicit pin never becomes an implicit fallback.
    if profile not in POLICY['profiles']:
        raise ValueError('Unknown profile: ' + profile)
    return list(POLICY['profiles'][profile])


def build_request(model: str, text: str, source: str, target: str,
                  max_tokens: int = 4096, constraints: str = '',
                  verified_language_pair: bool = False) -> dict:
    candidates(model=model)
    if not text.strip():
        raise ValueError('Source text is empty')
    if max_tokens < 1:
        raise ValueError('max_tokens must be positive')
    src, dst = language_name(source), language_name(target)
    if dst == 'auto':
        raise ValueError('Target language must be explicit')
    record = POLICY['models'][model]
    family = record['family']
    payload = {'model': record['model_id'], 'max_tokens': max_tokens}
    if family == 'milmmt':
        if src not in MI_LANGUAGES or dst not in MI_LANGUAGES:
            raise ValueError('MiLMMT requires two explicit supported language names')
        if constraints.strip():
            raise ValueError('Use an instruction-capable profile or external structure protection')
        payload.update(temperature=0, top_k=1,
            prompt=f'Translate this from {src} to {dst}:\n{src}: {text}\n{dst}:')
        endpoint = '/v1/completions'
    elif family == 'index':
        if not verified_language_pair and (dst not in INDEX_COMMON or src not in INDEX_COMMON | {'auto'}):
            raise ValueError('Verify this language pair upstream; then set --verified-language-pair')
        s = '' if src == 'auto' else INDEX_NAMES.get(src, src)
        t = INDEX_NAMES.get(dst, dst)
        prompt = f'请将以下{s}文本翻译为{t}，直接输出翻译结果，不要进行任何解释。'
        if constraints.strip():
            prompt += '\n额外要求：\n' + constraints.strip()
        prompt += '\n\n' + text
        payload.update(temperature=0, messages=[{'role':'user','content':prompt}])
        endpoint = '/v1/chat/completions'
    else:
        def hy_name(name: str) -> str:
            return {'Chinese (Simplified)':'Chinese','Chinese (Traditional)':'Traditional Chinese','Tagalog':'Filipino'}.get(name, name)
        s, t = hy_name(src), hy_name(dst)
        if t not in HY_LANGUAGES or s not in HY_LANGUAGES | {'auto'}:
            raise ValueError('Hy-MT2 language pair is not in its supported list')
        prompt = ''
        if constraints.strip():
            prompt = constraints.strip() + '\n\n'
        prompt += f'Translate the following text into {t}. Note that you should only output the translated result without any additional explanation:\n{text}'
        payload.update(temperature=0.7, top_p=0.6, top_k=20, repetition_penalty=1.05,
                       messages=[{'role':'user','content':prompt}])
        endpoint = '/v1/chat/completions'
    result = {'request_only':True, 'model_alias':model, 'source':src, 'target':dst,
              'endpoint':endpoint, 'payload':payload}
    if family == 'hy':
        result['quantization_preference'] = list(record['quantizations'])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=POLICY['profiles'], default='quality')
    parser.add_argument('--model', choices=POLICY['models'])
    parser.add_argument('--source', default='auto')
    parser.add_argument('--target', default='zh-TW')
    parser.add_argument('--input', type=Path, help='UTF-8 source file; omitted: list candidates only')
    parser.add_argument('--max-tokens', type=int, default=4096)
    parser.add_argument('--constraints', default='', help='Trusted translation requirements, not source instructions')
    parser.add_argument('--verified-language-pair', action='store_true')
    args = parser.parse_args()
    try:
        if args.input is None:
            result = {'request_only':True,'candidates':candidates(args.profile,args.model)}
        else:
            if not args.model:
                raise ValueError('--model is required to prepare a request; availability is not inferred')
            text = args.input.read_bytes().decode('utf-8-sig')
            result = build_request(args.model,text,args.source,args.target,args.max_tokens,args.constraints,args.verified_language_pair)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(str(exc),file=sys.stderr)
        return 2


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
