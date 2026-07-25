# -*- coding: utf-8 -*-
"""
convert_images.py — カード画像を軽量WebPに変換して GitHub Pages の1GB制限に収めるツール

使い方:
  1. このスクリプトを images フォルダの「1つ上」（index.html と同じ場所）に置く
  2. 初回のみ:  pip install pillow
  3. 実行:      python convert_images.py
  4. images_webp フォルダが出来るので、中身を確認したら
     旧 images フォルダを削除し、images_webp を images にリネームする

元の images フォルダは書き換えないので、失敗しても元に戻せる。
"""
import os
from PIL import Image

SRC_DIR = 'images'
DST_DIR = 'images_webp'
MAX_W = 400        # 横幅の上限（シミュレータ内の最大表示は約220pxなので十分）
QUALITY = 82       # WebP品質。小さくするとさらに軽くなるが画質が落ちる


def human(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f'{n:.1f} {unit}'
        n /= 1024


def main():
    if not os.path.isdir(SRC_DIR):
        print(f'!! {SRC_DIR} フォルダが見つかりません。index.html と同じ場所に置いてください。')
        return

    os.makedirs(DST_DIR, exist_ok=True)

    files = [f for f in sorted(os.listdir(SRC_DIR))
             if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    print(f'{len(files)} 枚を変換します（横幅{MAX_W}px / 品質{QUALITY}）\n')

    src_total = dst_total = 0
    done = skipped = failed = 0

    for i, name in enumerate(files, 1):
        src = os.path.join(SRC_DIR, name)
        dst = os.path.join(DST_DIR, os.path.splitext(name)[0] + '.webp')
        src_total += os.path.getsize(src)

        if os.path.exists(dst):          # 途中で止めても再実行で続きから進む
            dst_total += os.path.getsize(dst)
            skipped += 1
            continue

        try:
            with Image.open(src) as im:
                im = im.convert('RGB')
                if im.width > MAX_W:
                    h = round(im.height * MAX_W / im.width)
                    im = im.resize((MAX_W, h), Image.LANCZOS)
                im.save(dst, 'WEBP', quality=QUALITY, method=6)
            dst_total += os.path.getsize(dst)
            done += 1
        except Exception as e:
            print(f'  変換失敗: {name} ({e})')
            failed += 1

        if i % 500 == 0:
            print(f'  {i}/{len(files)} 枚完了')

    print(f'\n変換: {done}枚 / スキップ(既存): {skipped}枚 / 失敗: {failed}枚')
    print(f'変換前: {human(src_total)}')
    print(f'変換後: {human(dst_total)}')
    if src_total:
        print(f'削減率: {100 - dst_total / src_total * 100:.1f}%')
    print(f'\n{DST_DIR} を確認してください。問題なければ images を削除し、')
    print(f'{DST_DIR} を images にリネームしてください。')


if __name__ == '__main__':
    main()
