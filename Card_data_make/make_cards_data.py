# -*- coding: utf-8 -*-
"""
make_cards_data.py — カードJSONから cards-data.js を再生成するツール

使い方:
  1. スクレイパーが出力したカードJSON（全シリーズ分）を1つのフォルダに集める
  2. このスクリプトをそのフォルダに置く
  3. コマンドプロンプト/PowerShellでそのフォルダに移動して実行:
       python make_cards_data.py
  4. 出来上がった cards-data.js を index.html と同じ場所に上書きコピー

これだけで、シミュレータに新シリーズが追加される。index.htmlは触らなくていい。
"""
import json, glob, re, os

COLORS = '黄赤青緑紫'

def derive_color(c):
    for src in (c.get('発生エナジー記号', ''), c.get('発生エナジー', ''), c.get('必要エナジー', '')):
        for ch in str(src):
            if ch in COLORS:
                return ch
    return '無'

def derive_work(series):
    s = series
    s = re.sub(r'\s*NEW CARD SELECTION$', '', s)
    s = re.sub(r'\s*Vol\.\d+\s+(UA|EX|PC)\d+\w*$', '', s)   # Vol.2 / Vol.3 …のどれでも削る
    s = re.sub(r'\s*(UA|EX|PC)\d+\w*$', '', s)
    return s.strip()

def derive_max(eff):
    m = re.search(r'※このカードはデッキに(\d+)枚まで入れられる', eff or '')
    return int(m.group(1)) if m else 4

def req_num(req):
    m = re.search(r'(\d+)', str(req or ''))
    return int(m.group(1)) if m else 0

def trig_kind(trig):
    m = re.match(r'【(.+?)】', trig or '')
    return m.group(1) if m else ''

out = []
seen = set()
for fp in sorted(glob.glob('*.json')):
    with open(fp, encoding='utf-8') as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f'!! {fp} を読めなかった: {e}')
            continue
    if not isinstance(data, list):
        continue
    n = 0
    for c in data:
        no = c.get('カード番号')
        if not no or no in seen:      # 同じカード番号の重複は最初の1件だけ採用
            continue
        seen.add(no)
        out.append({
            'no': no, 'name': c['カード名'],
            'work': derive_work(c['シリーズ']), 'series': c['シリーズ'],
            'rar': c['レアリティ'], 'bp': c['BP'], 'ap': c['消費AP'],
            'type': c['カード種類'], 'trait': c['特徴'],
            'gen': c['発生エナジー'], 'req': c['必要エナジー'],
            'reqN': req_num(c['必要エナジー']),
            'eff': c['効果'], 'trig': c['トリガー'],
            'trigK': trig_kind(c['トリガー']),
            'img': c['画像ファイル名'],
            'color': derive_color(c), 'max': derive_max(c['効果']),
        })
        n += 1
    print(f'{fp}: {n}枚')

with open('cards-data.js', 'w', encoding='utf-8') as f:
    f.write('const CARD_DATA=' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n')

works = sorted(set(c['work'] for c in out))
print(f'\n完了: {len(out)}枚 / {len(works)}作品 -> cards-data.js '
      f'({os.path.getsize("cards-data.js") / 1e6:.2f} MB)')
