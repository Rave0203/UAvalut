# -*- coding: utf-8 -*-
"""
get_card.py — 公式サイトからカードを取得し、軽量WebPに変換して images フォルダへ入れるツール

このスクリプト1本で、次の3つを一度に行います。
  (1) 公式サイト（unionarena-tcg.com）から、指定した弾のカード情報を取得
  (2) カード画像をダウンロードし、その場で軽量WebPに変換
  (3) 変換した画像を UAvalut の images フォルダへ直接保存
      （元のPNGはディスクに残しません。残したい場合は下の SAVE_ORIGINAL_PNG を True に）

カード情報のJSONは Card_data_make/cards_data/ に弾ごとに保存されます。
そのあと make_cards_data.py を実行すると cards-data.js が出来上がります。

--- 使い方 -------------------------------------------------------------
  1. 初回のみ、必要なものを入れる:
        pip install playwright pillow
        playwright install chromium
  2. 下の SERIES_LIST で、取得したい弾の行だけ先頭の # を外す
     （取得済みの弾は # を付けたままにしておく。全部外すと数時間かかります）
  3. このフォルダで実行:
        python get_card.py
  4. 画像は ../images/ に、JSONは ./cards_data/ に入る
  5. 続けて make_cards_data.py を実行して cards-data.js を作り直す

途中で止めても、既にWebPがある画像は飛ばして続きから進みます。
------------------------------------------------------------------------
"""
import os
import io
import json
import re
from PIL import Image
from playwright.sync_api import sync_playwright

# ===== 設定 =============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))          # Card_data_make フォルダ
REPO_DIR   = os.path.dirname(SCRIPT_DIR)                          # index.html がある場所
IMAGES_DIR = os.path.join(REPO_DIR, "images")                     # 画像の最終的な置き場
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "cards_data")               # カードJSONの置き場

MAX_W   = 400          # 画像の横幅の上限（シミュレータ内の最大表示は約220pxなので十分）
QUALITY = 82           # WebPの品質。下げるとさらに軽くなるが画質が落ちる
SAVE_ORIGINAL_PNG = False   # True にすると変換前のPNGも cards_data/images_png/ に残す
OVERWRITE_IMAGE   = False   # True にすると既にあるWebPも取り直して上書きする

COLOR_CHARS = "赤青黄緑紫"

# 取得する全弾のリスト（値, シリーズ名）。取得したい弾だけ先頭の # を外す
SERIES_LIST = [
    #("570001", "コードギアス UA01ST"), ("570101", "コードギアス UA01BT"), ("570202", "コードギアス Vol.2 EX02BT"),
    #("570002", "呪術廻戦 UA02ST"), ("570102", "呪術廻戦 UA02BT"), ("570204", "呪術廻戦 Vol.2 EX04BT"), ("570702", "呪術廻戦 NEW CARD SELECTION"),
    #("570003", "HUNTER×HUNTER UA03ST"), ("570103", "HUNTER×HUNTER UA03BT"), ("570201", "HUNTER×HUNTER Vol.2 EX01BT"),
    #("570004", "アイマス シャニ UA04ST"), ("570104", "アイマス シャニ UA04BT"), ("570203", "アイマス シャニ Vol.2 EX03BT"), ("570301", "アイマス シャニ PC01BT"),
    #("570005", "鬼滅の刃 UA05ST"), ("570105", "鬼滅の刃 UA05BT"), ("570205", "鬼滅の刃 Vol.2 EX05BT"), ("570701", "鬼滅の刃 NEW CARD SELECTION"),
    #("570006", "Tales of ARISE UA06ST"), ("570106", "Tales of ARISE UA06BT"),
    #("570007", "転スラ UA07ST"), ("570107", "転スラ UA07BT"), ("570209", "転スラ Vol.2 EX09BT"),
    #("570008", "BLEACH UA08ST"), ("570108", "BLEACH UA08BT"), ("570207", "BLEACH Vol.2 EX07BT"), ("570704", "BLEACH NEW CARD SELECTION"),
    #("570009", "僕とロボコ UA09ST"), ("570109", "僕とロボコ UA09BT"),
    #("570010", "ヒロアカ UA10ST"), ("570110", "ヒロアカ UA10BT"), ("570206", "ヒロアカ Vol.2 EX06BT"),
    #("570011", "銀魂 UA11ST"), ("570111", "銀魂 UA11BT"),
    #("570012", "ブルーロック UA12ST"), ("570112", "ブルーロック UA12BT"), ("570703", "ブルーロック NEW CARD SELECTION"),
    #("570013", "鉄拳7 UA13ST"), ("570113", "鉄拳7 UA13BT"),
    #("570014", "Dr.STONE UA14ST"), ("570114", "Dr.STONE UA14BT"),
    #("570015", "SAO UA15ST"), ("570115", "SAO UA15BT"), ("570208", "SAO Vol.2 EX08BT"),
    #("570016", "SYNDUALITY Noir UA16ST"), ("570116", "SYNDUALITY Noir UA16BT"),
    #("570017", "トリコ UA17ST"), ("570117", "トリコ UA17BT"),
    #("570018", "NIKKE UA18ST"), ("570118", "NIKKE UA18BT"), ("570302", "NIKKE PC02BT"),
    #("570019", "ハイキュー UA19ST"), ("570119", "ハイキュー UA19BT"),
    #("570020", "ブラッククローバー UA20ST"), ("570120", "ブラッククローバー UA20BT"),
    #("570021", "幽遊白書 UA21ST"), ("570121", "幽遊白書 UA21BT"),
    #("570122", "GAMERA UA22BT"),
    #("570023", "進撃の巨人 UA23ST"), ("570123", "進撃の巨人 UA23BT"), ("570210", "進撃の巨人 Vol.2 EX10BT"),
    #("570124", "SHY UA24BT"),
    #("570125", "アンデッドアンラック UA25BT"),
    #("570126", "100カノ UA26BT"),
    #("570127", "学園アイマス UA27BT"), ("570213", "学園アイマス Vol.2 EX13BT"),
    #("570128", "怪獣8号 UA28BT"),
    #("570029", "仮面ライダー UA29ST"), ("570129", "仮面ライダー UA29BT"), ("570212", "仮面ライダー Vol.2 EX12BT"),
    #("570030", "アークナイツ UA30ST"), ("570130", "アークナイツ UA30BT"), ("570211", "アークナイツ Vol.2 EX11BT"),
    #("570031", "まどマギ UA31ST"), ("570131", "まどマギ UA31BT"),
    #("570132", "シャンフロ UA32BT"),
    #("570133", "2.5次元の誘惑 UA33BT"),
    #("570134", "コードギアス 奪還のロゼ UA34BT"),
    #("570035", "ワンパンマン UA35ST"), ("570135", "ワンパンマン UA35BT"),
    #("570036", "マクロス UA36ST"), ("570136", "マクロス UA36BT"), ("570214", "マクロス Vol.2 EX14BT"),
    #("570037", "鋼の錬金術師 UA37ST"), ("570137", "鋼の錬金術師 UA37BT"),
    #("570138", "WIND BREAKER UA38BT"), ("570501", "WIND BREAKER PREMIUM CARD SET"),
    #("570139", "キン肉マン UA39BT"),
    #("570040", "リゼロ UA40ST"), ("570140", "リゼロ UA40BT"),
    #("570041", "るろうに剣心 UA41ST"), ("570141", "るろうに剣心 UA41BT"),
    #("570042", "物語シリーズ UA42ST"), ("570142", "物語シリーズ UA42BT"),
    #("570143", "SAKAMOTO DAYS UA43BT"),
    #("570044", "エヴァ UA44ST"), ("570144", "エヴァ UA44BT"),
    #("570145", "To LOVEる UA45BT"),
    #("570146", "カグラバチ UA46BT"),
    #("570047", "東京喰種 UA47ST"), ("570147", "東京喰種 UA47BT"),
    #("570048", "キングダム UA48ST"), ("570148", "キングダム UA48BT"),
    #("570149", "魔都精兵のスレイブ UA49BT"),
    #("570150", "犬夜叉 UA50BT"),
    #("570151", "俺だけレベルアップな件 UA51BT"),
    #("570152", "陰の実力者 UA52BT"),
    #("570153", "チェンソーマン UA53BT"),
    #("570154", "無職転生 UA54BT"),
    #("570901", "プロモーションカード"),
    #("570801", "限定商品収録カード"),
    ("570055", "アイマス シンデレラ UA55ST"), ("570155", "アイマス シンデレラ UA55BT"),
    #("570215", "BLEACH Vol.3 EX15BT"),
    #("570401", "BLEACH UA01DC"),
    ("570156", "グレンラガン UA56BT"),
]

# ===== カード情報の読み取り =============================================
def energy_generated(detail):
    img = detail.query_selector(".generatedEnergyData .cardDataContents img")
    if not img:
        return "", ""
    alt = (img.get_attribute("alt") or "").strip()
    if alt in ("", "-"):
        return "", ""
    color = next((c for c in alt if c in COLOR_CHARS), "")
    return color + str(len(alt)), alt

def energy_need(detail):
    imgs = detail.query_selector_all(".needEnergyData .cardDataContents img")
    text = "".join((im.get_attribute("alt") or "") for im in imgs).strip()
    return "" if text in ("", "-") else text

def text_with_icons(detail, class_name):
    node = detail.query_selector("." + class_name + " .cardDataContents")
    if not node:
        return ""
    return node.evaluate("""
        el => {
            const clone = el.cloneNode(true);
            clone.querySelectorAll('img').forEach(img => {
                const alt = img.getAttribute('alt') || '';
                img.replaceWith(document.createTextNode('【' + alt + '】'));
            });
            return clone.textContent.replace(/\\s+/g, ' ').trim();
        }
    """)

def get_row(detail, title):
    for row in detail.query_selector_all(".cardDataCol"):
        t = row.query_selector(".cardDataTit")
        c = row.query_selector(".cardDataContents")
        if t and c and title in t.inner_text():
            return c.inner_text().strip()
    return ""

def safe_name(name):
    # フォルダ名・ファイル名に使えない文字を _ に置き換える
    return re.sub(r'[\\/:*?"<>|]', "_", name)

def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}"
        n /= 1024

# ===== 画像: ダウンロード → WebP変換 → images へ保存 ====================
def fetch_and_convert(page, img_url, img_name, stats):
    """
    画像を1枚ダウンロードし、その場でWebPに変換して images フォルダへ保存する。
    戻り値: True=保存した / False=失敗した / None=既にあるので飛ばした
    """
    webp_name = os.path.splitext(img_name)[0] + ".webp"
    webp_path = os.path.join(IMAGES_DIR, webp_name)

    if os.path.exists(webp_path) and not OVERWRITE_IMAGE:
        stats["skipped"] += 1
        return None

    try:
        resp = page.request.get(img_url)
        if not resp.ok:
            print(f"    画像の取得に失敗: {img_name}（HTTP {resp.status}）")
            stats["failed"] += 1
            return False
        raw = resp.body()
    except Exception as e:
        print(f"    画像の取得に失敗: {img_name}（{e}）")
        stats["failed"] += 1
        return False

    stats["src_bytes"] += len(raw)

    if SAVE_ORIGINAL_PNG:
        png_dir = os.path.join(OUTPUT_DIR, "images_png")
        os.makedirs(png_dir, exist_ok=True)
        with open(os.path.join(png_dir, img_name), "wb") as f:
            f.write(raw)

    try:
        with Image.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            if im.width > MAX_W:
                h = round(im.height * MAX_W / im.width)
                im = im.resize((MAX_W, h), Image.LANCZOS)
            im.save(webp_path, "WEBP", quality=QUALITY, method=6)
    except Exception as e:
        print(f"    WebP変換に失敗: {img_name}（{e}）")
        stats["failed"] += 1
        return False

    stats["dst_bytes"] += os.path.getsize(webp_path)
    stats["saved"] += 1
    return True

# ===== 本体 =============================================================
def main():
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    targets = [s for s in SERIES_LIST]
    if not targets:
        print("!! SERIES_LIST が空です。取得したい弾の行の # を外してください。")
        return

    print(f"画像の保存先: {IMAGES_DIR}")
    print(f"JSONの保存先: {OUTPUT_DIR}")
    print(f"対象: {len(targets)}弾（横幅{MAX_W}px / 品質{QUALITY}のWebPに変換します）")

    stats = {"saved": 0, "skipped": 0, "failed": 0, "src_bytes": 0, "dst_bytes": 0}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)   # 画面なし（高速）で回す
        page = browser.new_page()

        # 弾を1つずつ処理する
        for series_value, series_name in targets:
            try:
                print(f"\n===== {series_name} を取得中 =====")

                page.goto("https://www.unionarena-tcg.com/jp/cardlist/index.php?search=true")
                page.select_option("#series", series_value, force=True)
                page.wait_for_timeout(500)
                page.eval_on_selector("#series", "el => el.form.submit()")
                page.wait_for_load_state("networkidle")

                links = page.query_selector_all(".cardlistCol .cardImgCol .modalCardDataOpen")
                card_numbers = []
                for link in links:
                    m = re.search(r"card_no=(.+)", link.get_attribute("href"))
                    if m:
                        card_numbers.append(m.group(1))

                print(f"  {len(card_numbers)} 枚見つかりました")
                if not card_numbers:
                    continue

                all_cards = []
                for i, no in enumerate(card_numbers, 1):
                    url = "https://www.unionarena-tcg.com/jp/cardlist/detail_iframe.php?card_no=" + no
                    page.goto(url)
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(500)

                    detail = page.query_selector(".cardDetailCol")
                    if not detail:
                        print(f"    [{i}/{len(card_numbers)}] {no} … 取得失敗。スキップ")
                        continue

                    name_el = detail.query_selector(".cardNameCol")
                    name = name_el.inner_text().split("\n")[0].strip() if name_el else ""
                    rare_el = detail.query_selector(".rareData")
                    rare = rare_el.inner_text().strip() if rare_el else ""
                    gen_total, gen_raw = energy_generated(detail)

                    img_name = no.replace("/", "_").replace(":", "_") + ".png"
                    img_url = "https://www.unionarena-tcg.com/jp/images/cardlist/card/" + img_name

                    card = {
                        "カード番号": no,
                        "カード名": name,
                        "シリーズ": series_name,
                        "レアリティ": rare,
                        "BP": get_row(detail, "BP"),
                        "消費AP": get_row(detail, "AP"),
                        "カード種類": get_row(detail, "カード種類"),
                        "特徴": get_row(detail, "特徴"),
                        "発生エナジー": gen_total,
                        "発生エナジー記号": gen_raw,
                        "必要エナジー": energy_need(detail),
                        "効果": text_with_icons(detail, "effectData"),
                        "トリガー": text_with_icons(detail, "triggerData"),
                        "画像URL": img_url,
                        "画像ファイル名": img_name,     # index.html が .webp に読み替えるのでPNG名のまま持つ
                    }
                    all_cards.append(card)

                    # 取得したその場でWebPに変換して images フォルダへ入れる
                    fetch_and_convert(page, img_url, img_name, stats)

                    if i % 20 == 0:
                        print(f"    {i}/{len(card_numbers)} 枚完了"
                              f"（画像 保存{stats['saved']} / 既存{stats['skipped']} / 失敗{stats['failed']}）")

                # この弾のJSONを保存
                json_path = os.path.join(OUTPUT_DIR, safe_name(series_name) + ".json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(all_cards, f, ensure_ascii=False, indent=2)
                print(f"  → {json_path} に {len(all_cards)} 件保存")

            except Exception as e:
                # この弾でエラーが出ても、止まらず次の弾へ進む
                print(f"  !! {series_name} でエラー: {e} → この弾を飛ばして次へ")
                continue

        browser.close()

    print("\n★ 全弾の取得が完了しました ★")
    print(f"画像: 保存{stats['saved']}枚 / 既にあり{stats['skipped']}枚 / 失敗{stats['failed']}枚")
    if stats["src_bytes"]:
        print(f"  変換前 {human(stats['src_bytes'])} → 変換後 {human(stats['dst_bytes'])}"
              f"（{100 - stats['dst_bytes'] / stats['src_bytes'] * 100:.1f}% 削減）")
    print(f"画像の保存先: {IMAGES_DIR}")
    print("\n続けて make_cards_data.py を実行すると cards-data.js が出来上がります。")

if __name__ == "__main__":
    main()
