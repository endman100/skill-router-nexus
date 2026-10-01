from pathlib import Path
import importlib.util
import json
import re
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'Writing-and-Content/translate'
LEGACY = [
 'Writing-and-Content/baoyu-translate','Writing-and-Content/baoyu-skills-baoyu-translate',
 'Writing-and-Content/translate-polisher','Writing-and-Content/translate-with-milmmt',
 'Writing-and-Content/translate-with-hy-mt2','Document-Generation/visa-doc-translate',
]

def load(name):
    spec=importlib.util.spec_from_file_location(name,SKILL/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

request=load('model_request')
chunk=load('chunk_text')


def test_one_canonical_flat_skill():
    text=(SKILL/'SKILL.md').read_text(encoding='utf-8')
    assert 'name: translate\n' in text
    assert len(list(SKILL.rglob('SKILL.md')))==1
    assert len(text.splitlines())<500
    assert all(not (ROOT/p).exists() for p in LEGACY)
    assert not list(SKILL.rglob('*router*.py'))


def test_relative_references_exist():
    for p in SKILL.rglob('*.md'):
        for ref in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' in ref or ref.startswith('#'):
                continue
            assert (p.parent/ref.split('#')[0]).exists(),(p,ref)


def test_profiles_have_deterministic_order():
    assert request.candidates()==['milmmt-12b','index-9b','milmmt-4b','index-2b','hy-mt2','milmmt-1b']
    assert request.candidates('instructions')==['index-9b','index-2b','hy-mt2']
    assert request.candidates('fast')==['index-2b','hy-mt2','milmmt-1b']
    assert request.candidates('cpu')==['hy-mt2']


@pytest.mark.parametrize('model',list(request.POLICY['models']))
def test_explicit_pin_is_not_replaced(model):
    assert request.candidates('fast',model)==[model]


def test_unknown_model_rejected():
    with pytest.raises(ValueError): request.candidates(model='invented')


def test_index_prompt_and_sampling():
    result=request.build_request('index-9b','Keep {name}: 42','en','zh-TW',constraints='Preserve {name}.')
    assert result['request_only'] is True
    assert result['payload']['model']=='IndexTeam/Index-Translate-9B'
    assert result['payload']['temperature']==0
    assert result['endpoint']=='/v1/chat/completions'
    assert [m['role'] for m in result['payload']['messages']]==['user']
    assert '繁体中文' in result['payload']['messages'][0]['content']
    assert result['payload']['messages'][0]['content'].endswith('Keep {name}: 42')


def test_index_unknown_pair_requires_verification():
    with pytest.raises(ValueError): request.build_request('index-2b','sample','Welsh','zh-TW')
    assert request.build_request('index-2b','sample','Welsh','zh-TW',verified_language_pair=True)['request_only']


def test_milmmt_raw_prompt():
    result=request.build_request('milmmt-12b','Hello.','en','zh-TW')
    assert result['endpoint']=='/v1/completions'
    assert result['payload']['prompt']=='Translate this from English to Chinese (Traditional):\nEnglish: Hello.\nChinese (Traditional):'
    assert result['payload']['top_k']==1
    assert result['payload']['temperature']==0
    assert 'messages' not in result['payload']


@pytest.mark.parametrize('source,target,extra',[('auto','en',''),('Klingon','en',''),('en','auto',''),('en','ja','Be formal')])
def test_milmmt_rejects_invalid_contract(source,target,extra):
    with pytest.raises(ValueError): request.build_request('milmmt-4b','Hello',source,target,constraints=extra)


def test_hy_contract_and_quantization():
    result=request.build_request('hy-mt2','Hello','en','zh-TW')
    payload=result['payload']
    assert payload['temperature']==0.7 and payload['top_p']==0.6 and payload['top_k']==20
    assert payload['repetition_penalty']==1.05
    assert [m['role'] for m in payload['messages']]==['user']
    assert 'Traditional Chinese' in payload['messages'][0]['content']
    assert result['quantization_preference']==['Q8_0','Q6_K','Q4_K_M']


@pytest.mark.parametrize('text,max_tokens',[('',32),('hello',0)])
def test_bad_requests_fail(text,max_tokens):
    with pytest.raises(ValueError): request.build_request('index-2b',text,'auto','en',max_tokens=max_tokens)


def test_lossless_markdown_chunks():
    text='---\r\ntitle: Original\r\n---\r\n\r\n# Heading\r\n\r\n中文測試。\r\n\r\n```py\r\nprint(42)\r\n\r\nprint(1)\r\n```\r\n\r\nTail\r\n'
    parts=chunk.split_chunks(text,65)
    assert ''.join(parts)==text
    assert all(len(p)<=65 for p in parts)
    assert any('print(42)\r\n\r\nprint(1)' in p for p in parts)


@pytest.mark.parametrize('text,limit',[('```\nx\n',50),('---\na: b\n',50),('x'*20,10),('x',0)])
def test_invalid_chunking_fails_without_truncation(text,limit):
    with pytest.raises(ValueError): chunk.split_chunks(text,limit)


def test_chunk_files_preserve_bytes_and_never_overwrite(tmp_path):
    source=tmp_path/'source.md'; source.write_bytes('第一段\r\n\r\n第二段\r\n'.encode())
    out=tmp_path/'new'
    manifest=chunk.write_chunks(source,out,9)
    assert b''.join((out/item['file']).read_bytes() for item in manifest['chunks'])==source.read_bytes()
    assert manifest['token_budget_verified'] is False
    with pytest.raises(FileExistsError): chunk.write_chunks(source,out,9)
    assert (out/'manifest.json').exists()


def test_policy_and_safe_document_contracts():
    policy=json.loads((SKILL/'references/model-policy.json').read_text(encoding='utf-8'))
    assert all('-Pretrain' not in m['model_id'] for m in policy['models'].values())
    docs=(SKILL/'references/documents.md').read_text(encoding='utf-8')
    assert 'Machine-assisted translation; not certified.' in docs
    assert 'This is a certified English translation' not in docs
    assert 'ImageOps.exif_transpose' in docs
    assert '護照' in docs


def test_legacy_preferences_and_glossaries_retained():
    text=(SKILL/'references/preferences.md').read_text(encoding='utf-8')
    assert '.baoyu-skills/baoyu-translate/EXTEND.md' in text
    assert 'glossaries' in text and 'chunk_max_words' in text
    for name in ['glossary-en-zh.md','glossary-en-ja.md','glossary-zh-ja.md']:
        text=(SKILL/'references'/name).read_text(encoding='utf-8')
        assert text.count('\n|')>=17


def test_bom_frontmatter_is_atomic():
    text='\ufeff---\r\na: b\r\n\r\nc: d\r\n---\r\n\r\nBody\r\n'
    parts=chunk.split_chunks(text,30)
    assert ''.join(parts)==text
    assert any('a: b\r\n\r\nc: d' in p for p in parts)
    with pytest.raises(ValueError): chunk.split_chunks(text,17)


def test_tilde_fence_is_atomic():
    text='Title\n\n~~~~txt\n\nvalue\n~~~\n~~~~\n\nEnd\n'
    assert ''.join(chunk.split_chunks(text,40))==text
    with pytest.raises(ValueError): chunk.split_chunks(text,12)


def test_cli_requires_explicit_model_for_payload(tmp_path):
    source=tmp_path/'source.txt'; source.write_text('Hello',encoding='utf-8')
    result=subprocess.run([sys.executable,'-B',str(SKILL/'scripts/model_request.py'),'--input',str(source)],capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==2
    assert '--model is required' in result.stderr


def test_profile_cli_does_not_translate():
    result=subprocess.run([sys.executable,'-B',str(SKILL/'scripts/model_request.py'),'--profile','fast'],capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)=={'request_only':True,'candidates':['index-2b','hy-mt2','milmmt-1b']}
