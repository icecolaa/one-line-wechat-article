#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一句话开稿：从主题搭出项目骨架（目录 + 文章骨架 + 素材清单）。

这是"一句话生成公众号文章"的第一步。它不写正文——正文由 AI 按你给的一句话
和 references/style-rules.md 来写；它负责把目录、清单、命令一次搭好。

用法（在项目根目录运行）：
    python <skill>/scripts/new_article.py --topic "一句话主题" [--slug 20261101]
        [--title "定稿标题"] [--images 截图目录] [--series "21 篇连载 · 第 5 篇"]

产出：
    articles/src/<slug>-<文件名>.md            文章骨架（标题、引言、小节占位）
    articles/src/<slug>-<文件名>.assets.json   素材清单（复制进来的截图已登记）
    pic/<slug>/素材/                           可选：从 --images 原样复制的截图
    并打印后续命令清单。

素材清单门禁由 check_assets.py 负责；排版合成见 build.py；一条龙见 run.py。
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
MD_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_size(p: Path):
    try:
        from PIL import Image
        with Image.open(p) as im:
            return im.size
    except Exception:
        return None


def slugify_default():
    return datetime.now().strftime("%Y%m%d")


def safe_stem(title: str, fallback: str) -> str:
    stem = re.sub(r"[\\/:*?\"<>|\s]+", "", title)[:16]
    return stem or fallback


def scaffold_md(topic: str, title: str, series: str, author: str) -> str:
    return f"""# {title}

> {series}。{topic}

（按 references/style-rules.md 写正文：短句一句一事、主谓相邻、不堆名词、不自造比喻。
结构建议：开头场景 → 我的判断（加粗一句）→ 2~4 个小节（每节配图）→ 写在最后 + 下一篇预告。
图片用绝对正斜杠路径插进正文，图注写在 ![ ] 里，必须与 assets.json 的 caption 完全一致。）

## 小节一

（正文……）

![图注：必须与截图画面一致](E:/abs/path/to/截图.png)

## 小节二

（正文……）

## 写在最后

（正文……）

连载 x/y。文中界面来自开发环境，均为演示数据，不代表已上线产品。

---

*作者：{author}*
"""


def main():
    ap = argparse.ArgumentParser(description="一句话开稿：搭目录、骨架与素材清单")
    ap.add_argument("--topic", required=True, help="一句话主题")
    ap.add_argument("--title", default="", help="定稿标题（缺省先用主题占位，写完再改）")
    ap.add_argument("--slug", default=slugify_default(), help="日期目录名，如 20261101")
    ap.add_argument("--series", default="", help="系列标注，如 \"21 篇连载 · 第 5 篇\"")
    ap.add_argument("--author", default="", help="作者名（缺省取 config.brand.name）")
    ap.add_argument("--images", default="", help="可选：截图目录，原样复制进 pic/<slug>/素材/")
    a = ap.parse_args()

    skill_dir = Path(__file__).resolve().parent
    cfg = json.loads((skill_dir / "config.json").read_text(encoding="utf-8"))
    author = a.author or cfg["brand"]["name"]
    title = a.title or a.topic
    series = a.series or cfg["brand"]["series"]

    src_dir = Path(cfg["paths"]["article_src"])
    pic_dir = Path(cfg["paths"]["pic_root"]) / a.slug
    src_dir.mkdir(parents=True, exist_ok=True)

    stem = safe_stem(title, a.slug)
    md_path = src_dir / f"{a.slug}-{stem}.md"
    if md_path.exists():
        sys.exit(f"已存在同名稿子：{md_path}（换个 --slug 或 --title）")

    # 1. 素材：可选复制截图
    copied = []
    if a.images:
        img_src = Path(a.images)
        if not img_src.is_dir():
            sys.exit(f"截图目录不存在：{img_src}")
        dst = pic_dir / "素材"
        dst.mkdir(parents=True, exist_ok=True)
        seen_hashes = {}
        for f in sorted(img_src.iterdir()):
            if not f.is_file() or f.suffix.lower() not in IMG_EXTS:
                continue
            h = sha256_of(f)
            if h in seen_hashes:
                continue  # 字节级重复只留一份
            seen_hashes[h] = f.name
            shutil.copy2(f, dst / f.name)
            copied.append(dst / f.name)

    # 2. 文章骨架
    md_path.write_text(scaffold_md(a.topic, title, series, author), encoding="utf-8")

    # 3. 素材清单（有图就登记；图注留空，写完正文后回填）
    images_meta = []
    for p in copied:
        w, h = image_size(p) or ("", "")
        images_meta.append({
            "id": f"img-{p.stem[:24]}",
            "file": p.resolve().as_posix(),
            "required": True,
            "kind": "screenshot",
            "source": {
                "type": "screenshot",
                "path": p.resolve().as_posix(),
                "env": "待补：来源页面/环境",
                "data": "待补：真实数据还是演示数据",
                "sha256": sha256_of(p),
                "note": "原样复制，未缩放/裁切/重编码",
            },
            "usage": "待补：用在哪一节",
            "caption": "",
            "sha256": sha256_of(p),
            "width": w,
            "height": h,
        })

    manifest = {
        "schema_version": 1,
        "slug": a.slug,
        "article": md_path.resolve().as_posix(),
        "note": "逐图清单：required 图片缺文件、未引用、hash/尺寸/图注不符都会阻断；正文引用清单之外的本地图片同样阻断。",
        "cover": {
            "file": "",
            "required": True,
            "kind": "cover",
            "sha256": "",
            "width": 900,
            "height": 383,
            "usage": "封面 900x383：用 build.py 生成后回填 file/sha256",
        },
        "images": images_meta,
    }
    mpath = md_path.with_suffix(".assets.json")
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ 骨架已就绪")
    print(f"   文章     {md_path}")
    print(f"   素材清单 {mpath}")
    if copied:
        print(f"   截图     {len(copied)} 张 → {pic_dir / '素材'}")
    print("""
后续步骤（按序执行）：
  1. 按一句话主题写正文（结构见骨架内注释，文风见 references/style-rules.md），
     图片引用用绝对正斜杠路径，图注 = 截图画面事实。
  2. 回填 assets.json：每张图的 caption 必须与正文 ![图注] 完全一致；usage/env/data 补全。
  3. 生成封面与分享图（build.py cover-shot / share-poster），回填清单 cover 字段。
  4. 门禁：   python <skill>/scripts/check_assets.py --article <md路径>
  5. 预演：   python <skill>/scripts/run.py --article <md路径> --slug <slug> --theme cyan --dry-run
  6. 正式：   去掉 --dry-run（需要 wechat-ai-publisher 已配置公众号凭证）
""")


if __name__ == "__main__":
    main()
