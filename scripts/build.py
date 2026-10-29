#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把插画 + 中文文字合成为精确像素的成品图。

中文一律走 HTML 排版再截屏，不交给生图模型画字，
所以 900x383 / 1080x1080 / 1080x720 尺寸精确、文字一个不差。

用法：
    # 封面 900x383
    python build.py cover --art art.png --out pic/20261023/封面-900x383.png \
        --h1 "冰可乐" --sub "「<span class='hl'>7 年全栈</span><span class='slash'> / </span>从 GoTrip 出发」"

    # 分享图 1080x1080
    python build.py share --art art.png --out pic/20261023/分享图-1080x1080.png \
        --badge "21 篇连载" --h1 "用一个项目，<br>把 <span class='ai'>AI</span> 学明白" \
        --foot "冰可乐 <span class='slash'>/</span> 7 年全栈 <span class='slash'>/</span> 从 GoTrip 出发"

    # 正文插图 1080x720（可选字幕条）
    python build.py inline --art art.png --out pic/20261023/插图-01.png \
        --caption "先跑通一遍，再谈架构"

    # 截图型文章的 5:4 分享海报 1200x960（三张竖版卡片 = 三条主线）
    python build.py share-poster --art1 a.png --art2 b.png --art3 c.png \
        --out pic/20261024/分享图-5x4.png --h1 "三份清单<br>一段旅行" \
        --eyebrow "GoTrip · 开发手记" --sub "先跑通" --badge "21 篇连载 · 第 02 篇" --serial 02

    # 拼贴封面 900x383（小狗/机器人/明信片三张素材）
    python build.py collage-cover --dog dog.png --robot robot.png --photo postcard.png \
        --out pic/20261023/封面-collage-900x383-样张.png \
        --h1 "用一个项目<br>把 <span class='ai'>AI</span> 学明白" \
        --eyebrow "30 岁 · 重新出发" --badge "21 篇连载 · 第 01 篇"

    # 拼贴分享图 1080x1080
    python build.py collage-share --dog dog.png --robot robot.png --photo postcard.png \
        --out pic/20261023/分享图-collage-1080x1080-样张.png \
        --h1 "用一个项目<br>把 <span class='ai'>AI</span> 学明白" \
        --eyebrow "30 岁 · 7 年全栈" --sub "先跑通，再谈架构" --ep 1 --total 21

    # 拼贴正文插图 1080x720
    python build.py collage-inline --dog dog.png --robot robot.png --photo postcard.png \
        --out pic/20261023/插图-collage-1080x720.png \
        --h1 "先跑通一遍<br><span class='hl'>再谈架构</span>" \
        --eyebrow "GoTrip · 开发手记" --badge "21 篇连载 · 第 01 篇"
"""
import argparse
import base64
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # 技能的 scripts 目录
sys.path.insert(0, str(ROOT / "tools"))
from shot import shot  # noqa: E402

CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
TPL = ROOT / "templates"
BUILD = Path(CFG["paths"]["build"])
if not BUILD.is_absolute():
    BUILD = Path.cwd() / BUILD                  # 相对路径按项目根解析


def data_uri(p: Path) -> str:
    p = Path(p)
    suffix = p.suffix.lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".webp": "image/webp"}.get(suffix, "image/png")
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def render(tpl_name: str, out: Path, values: dict, w: int, h: int) -> Path:
    html = (TPL / tpl_name).read_text(encoding="utf-8")
    for k, v in values.items():
        html = html.replace("{{%s}}" % k, v)
    left = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", html)))
    if left:
        raise SystemExit(f"模板 {tpl_name} 还有没填的占位符：{left}")

    BUILD.mkdir(parents=True, exist_ok=True)
    tmp_html = BUILD / (Path(out).stem + ".html")
    tmp_html.write_text(html, encoding="utf-8")
    out = Path(out).resolve()
    shot(tmp_html, out, w, h)
    size = out.stat().st_size // 1024
    print(f"ok {out}  {w}x{h}  {size}KB")
    return out


def styled_tagline() -> str:
    return CFG["brand"]["tagline"].replace(" / ", ' <span class="slash">/</span> ')


def photo_caption() -> str:
    return CFG["brand"]["tagline"].split(" / ")[-1]


def series_badge() -> str:
    return f'{CFG["brand"]["series"]} · 第 01 篇'


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="kind", required=True)

    c = sub.add_parser("cover")
    c.add_argument("--art", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--h1", required=True)
    c.add_argument("--sub", default="")

    s = sub.add_parser("share")
    s.add_argument("--art", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--badge", default=CFG["brand"]["series"])
    s.add_argument("--h1", required=True)
    s.add_argument("--foot", default=None)

    i = sub.add_parser("inline")
    i.add_argument("--art", required=True)
    i.add_argument("--out", required=True)
    i.add_argument("--caption", default="")
    i.add_argument("--tag", default="")

    sp = sub.add_parser("share-poster")
    sp.add_argument("--art1", required=True, help="左卡片（行程）")
    sp.add_argument("--art2", required=True, help="中卡片（账目）")
    sp.add_argument("--art3", required=True, help="右卡片（行李）")
    sp.add_argument("--out", required=True)
    sp.add_argument("--h1", required=True)
    sp.add_argument("--eyebrow", default="")
    sp.add_argument("--sub", default="")
    sp.add_argument("--badge", default=series_badge())
    sp.add_argument("--serial", default="02")
    sp.add_argument("--stamp", default="出发")
    sp.add_argument("--year", default=str(datetime.now().year))

    ss = sub.add_parser("share-shot")
    ss.add_argument("--art1", required=True, help="左：行程截图")
    ss.add_argument("--art2", required=True, help="中：账目截图")
    ss.add_argument("--art3", required=True, help="右：行李截图")
    ss.add_argument("--out", required=True)
    ss.add_argument("--h1", required=True)
    ss.add_argument("--sub", default="")
    ss.add_argument("--badge", default=series_badge())
    ss.add_argument("--foot", default=None)

    cc = sub.add_parser("cover-shot")
    cc.add_argument("--art1", required=True, help="主手机截图（靠左、较大）")
    cc.add_argument("--art2", required=True, help="副手机截图（靠右、较小）")
    cc.add_argument("--out", required=True)
    cc.add_argument("--h1", required=True)
    cc.add_argument("--sub", default="")
    cc.add_argument("--badge", default=series_badge())

    cc = sub.add_parser("collage-cover")
    cc.add_argument("--dog", required=True)
    cc.add_argument("--robot", required=True)
    cc.add_argument("--photo", required=True)
    cc.add_argument("--out", required=True)
    cc.add_argument("--h1", required=True)
    cc.add_argument("--badge", default=series_badge())
    cc.add_argument("--eyebrow", default="")
    cc.add_argument("--sub", default=None)
    cc.add_argument("--stamp", default="出发")
    cc.add_argument("--year", default=str(datetime.now().year))

    cs = sub.add_parser("collage-share")
    cs.add_argument("--dog", required=True)
    cs.add_argument("--robot", required=True)
    cs.add_argument("--photo", required=True)
    cs.add_argument("--out", required=True)
    cs.add_argument("--h1", required=True)
    cs.add_argument("--badge", default=series_badge())
    cs.add_argument("--eyebrow", default="")
    cs.add_argument("--sub", default=None)
    cs.add_argument("--photo-cap", default=photo_caption())
    cs.add_argument("--foot", default=CFG["brand"]["name"])
    cs.add_argument("--foot-tag", default=None)
    cs.add_argument("--stamp", default="出发")
    cs.add_argument("--year", default=str(datetime.now().year))
    cs.add_argument("--ep", default="1")
    cs.add_argument("--total", default=CFG["brand"]["series"].split(" ")[0])

    ci = sub.add_parser("collage-inline")
    ci.add_argument("--dog", required=True)
    ci.add_argument("--robot", required=True)
    ci.add_argument("--photo", required=True)
    ci.add_argument("--out", required=True)
    ci.add_argument("--h1", required=True)
    ci.add_argument("--badge", default=series_badge())
    ci.add_argument("--eyebrow", default="")
    ci.add_argument("--sub", default=None)
    ci.add_argument("--stamp", default="出发")
    ci.add_argument("--year", default=str(datetime.now().year))
    ci.add_argument("--ep", default="01")

    a = ap.parse_args()
    art = data_uri(Path(a.art)) if getattr(a, "art", None) else ""

    if a.kind == "cover":
        sz = CFG["sizes"]["cover"]
        render("cover-900x383.html", Path(a.out),
               {"ART": art, "H1": a.h1, "SUB": a.sub}, sz["w"], sz["h"])
    elif a.kind == "share":
        sz = CFG["sizes"]["share"]
        foot = a.foot if a.foot is not None else (
            f'{CFG["brand"]["name"]} <span class="slash">/</span> '
            f'{CFG["brand"]["tagline"].replace(" / ", " <span class=\'slash\'>/</span> ")}')
        render("share-1080x1080.html", Path(a.out),
               {"ART": art, "BADGE": a.badge, "H1": a.h1, "FOOT": foot}, sz["w"], sz["h"])
    elif a.kind == "inline":
        sz = CFG["sizes"]["inline"]
        tag = f'<span class="tag">{a.tag}</span>' if a.tag else ""
        render("inline-1080x720.html", Path(a.out),
               {"ART": art, "CAPTION": a.caption, "TAG": tag,
                "CAP_CLASS": "" if a.caption else " empty"}, sz["w"], sz["h"])
    elif a.kind == "share-poster":
        sz = CFG["sizes"]["share54"]
        values = {
            "ART1": data_uri(Path(a.art1)),
            "ART2": data_uri(Path(a.art2)),
            "ART3": data_uri(Path(a.art3)),
            "BADGE": a.badge,
            "EYEBROW": a.eyebrow,
            "H1": a.h1,
            "SUB": a.sub if a.sub else styled_tagline(),
            "SERIAL": a.serial,
            "STAMP": a.stamp,
            "YEAR": a.year,
        }
        render("share-poster-1200x960.html", Path(a.out), values, sz["w"], sz["h"])
    elif a.kind == "share-shot":
        sz = CFG["sizes"]["share"]
        foot = a.foot if a.foot is not None else (
            f'{CFG["brand"]["name"]} <span class="slash">/</span> '
            f'{CFG["brand"]["tagline"].replace(" / ", " <span class=\'slash\'>/</span> ")}')
        values = {
            "ART1": data_uri(Path(a.art1)),
            "ART2": data_uri(Path(a.art2)),
            "ART3": data_uri(Path(a.art3)),
            "BADGE": a.badge,
            "H1": a.h1,
            "SUB": a.sub if a.sub else styled_tagline(),
            "FOOT": foot,
        }
        render("share-shot-1080x1080.html", Path(a.out), values, sz["w"], sz["h"])
    elif a.kind == "cover-shot":
        sz = CFG["sizes"]["cover"]
        values = {
            "ART1": data_uri(Path(a.art1)),
            "ART2": data_uri(Path(a.art2)),
            "BADGE": a.badge,
            "H1": a.h1,
            "SUB": a.sub if a.sub else styled_tagline(),
        }
        render("cover-shot-900x383.html", Path(a.out), values, sz["w"], sz["h"])
    elif a.kind == "collage-cover":
        sz = CFG["sizes"]["cover"]
        values = {
            "ART_DOG": data_uri(Path(a.dog)),
            "ART_ROBOT": data_uri(Path(a.robot)),
            "ART_PHOTO": data_uri(Path(a.photo)),
            "BADGE": a.badge,
            "EYEBROW": a.eyebrow,
            "H1": a.h1,
            "SUB": a.sub if a.sub is not None else styled_tagline(),
            "STAMP": a.stamp,
            "YEAR": a.year,
            "BRAND": CFG["brand"]["name"],
        }
        render("cover-collage-900x383.html", Path(a.out), values, sz["w"], sz["h"])
    elif a.kind == "collage-inline":
        sz = CFG["sizes"]["inline"]
        values = {
            "ART_DOG": data_uri(Path(a.dog)),
            "ART_ROBOT": data_uri(Path(a.robot)),
            "ART_PHOTO": data_uri(Path(a.photo)),
            "BADGE": a.badge,
            "EYEBROW": a.eyebrow,
            "H1": a.h1,
            "SUB": a.sub if a.sub is not None else styled_tagline(),
            "STAMP": a.stamp,
            "YEAR": a.year,
            "BRAND": CFG["brand"]["name"],
            "EP": a.ep,
        }
        render("inline-collage-1080x720.html", Path(a.out), values, sz["w"], sz["h"])
    else:
        sz = CFG["sizes"]["share"]
        values = {
            "ART_DOG": data_uri(Path(a.dog)),
            "ART_ROBOT": data_uri(Path(a.robot)),
            "ART_PHOTO": data_uri(Path(a.photo)),
            "BADGE": a.badge,
            "EYEBROW": a.eyebrow,
            "H1": a.h1,
            "SUB": a.sub if a.sub is not None else styled_tagline(),
            "PHOTO_CAP": a.photo_cap,
            "FOOT": a.foot,
            "FOOT_TAG": a.foot_tag if a.foot_tag is not None else styled_tagline(),
            "STAMP": a.stamp,
            "YEAR": a.year,
            "EP": a.ep,
            "TOTAL": a.total,
        }
        render("share-collage-1080x1080.html", Path(a.out), values, sz["w"], sz["h"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
