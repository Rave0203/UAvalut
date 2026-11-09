# -*- coding: utf-8 -*-
"""
update_cards_data.py — 今ある cards-data.js に、cards_data/ のJSONを差し込んで更新するツール

make_cards_data.py は「全弾のJSONから作り直す」ため、過去の弾のJSONが揃っていないと
カードが減ってしまいます。こちらは今ある cards-data.js を土台にするので、
新しく取得した弾のJSONだけあれば足ります。

  ・cards_data/ にあるJSONの弾が cards-data.js に既にあれば → その弾を丸ごと入れ替え
  ・まだ無い弾なら → 末尾に追加
  ・それ以外の弾には触りません

使い方（このフォルダで）:
    python update_cards_data.py
"""
import os, json, glob
from make_cards_data import to_entry

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR   = os.path.join(SCRIPT_DIR, "cards_data")
JS_PATH    = os.path.join(os.path.dirname(SCRIPT_DIR), "cards-data.js")
PREFIX     = "const CARD_DATA="
EOL        = "\n"

def load_js(path):
    with open(path, encoding="utf-8", newline="") as f:
        raw = f.read()
    global EOL
    EOL = "\r\n" if raw.endswith("\r\n") else "\n"   # 元ファイルの改行コードを引き継ぐ
    s = raw.strip()
    if not s.startswith(PREFIX):
        raise SystemExit(f"!! {path} の形式が想定と違います（{PREFIX} で始まっていません）")
    return json.loads(s[len(PREFIX):].rstrip(";"))

def main():
    old = load_js(JS_PATH)

    # JSONを弾ごとにまとめる（ファイル名順。同じカード番号は最初の1件だけ）
    fresh = {}      # series -> [entry, ...]
    for fp in sorted(glob.glob(os.path.join(JSON_DIR, "*.json"))):
        with open(fp, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"!! {os.path.basename(fp)} を読めなかった: {e}")
                continue
        if not isinstance(data, list) or not data:
            continue
        for c in data:
            if c.get("カード番号"):
                e = to_entry(c)
                fresh.setdefault(e["series"], []).append(e)

    # 入れ替える弾以外のカード番号（重複チェック用）
    keep_nos = {c["no"] for c in old if c["series"] not in fresh}

    def dedup(entries):
        res = []
        for e in entries:
            if e["no"] in keep_nos:
                continue
            keep_nos.add(e["no"])
            res.append(e)
        return res

    out, placed = [], set()
    for c in old:
        s = c["series"]
        if s in fresh:
            if s not in placed:             # 元の位置にまとめて差し込む
                out.extend(dedup(fresh[s]))
                placed.add(s)
            continue
        out.append(c)

    added = [s for s in fresh if s not in placed]
    for s in added:
        out.extend(dedup(fresh[s]))

    with open(JS_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(PREFIX + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";" + EOL)

    for s in fresh:
        mark = "追加" if s in added else "更新"
        print(f"  [{mark}] {s}: {sum(1 for c in out if c['series'] == s)}枚")
    works = sorted(set(c["work"] for c in out))
    print(f"\n完了: {len(old)}枚 → {len(out)}枚 / {len(works)}作品 -> cards-data.js "
          f"({os.path.getsize(JS_PATH) / 1e6:.2f} MB)")

if __name__ == "__main__":
    main()
