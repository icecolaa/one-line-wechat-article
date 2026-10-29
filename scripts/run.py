#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
wechat-cover 流水线编排器

一条命令把 Markdown 素材变成公众号草稿：
  1. 素材清单门禁（离线）：默认读取与文章同名的 <article>.assets.json，
     逐图校验存在 / hash / 尺寸 / 正文引用 / 图注；缺清单、缺图、未引用、
     正文引用不存在图片都会在上传前阻断。
  2. Markdown → 微信 HTML（doocs 主题）
  3. HTML 引用复核（required 图片必须进入 HTML）
  4. 封面压缩 + 正文图扫描上传 → 建草稿 + 归档

用法：
    python pipeline/run.py --article articles/src/20261023-开篇自述.md \
        --slug 20261023 --theme cyan [--dry-run] [--assets xxx.assets.json]

目录约定：
    pic/<slug>/                封面 / 分享图 / 正文插图
    articles/src/              输入 Markdown（清单与文章同名：<article>.assets.json）
    articles/published/        归档（HTML + meta，仅真实发布时写入）
    .build/<slug>/preview/     --dry-run 的全部产物（HTML + 素材检查报告）

dry-run 保证：不访问微信 API、不写入 articles/published、不建草稿。
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()                      # 约定：在项目根目录运行
SKILL_DIR = Path(__file__).resolve().parent
CFG = json.loads((SKILL_DIR / "config.json").read_text(encoding="utf-8"))
PY = CFG["paths"].get("python") or sys.executable


def _resolve_publisher_skill(p):
    """定位 wechat-ai-publisher 依赖技能（本机已安装路径或用户配置）。"""
    cands = []
    if p:
        cands.append(Path(p))
    cands += [
        Path.home() / ".workbuddy-ai" / "skills" / "wechat-ai-publisher",
        Path.home() / ".zcode" / "skills" / "wechat-ai-publisher",
        Path.home() / ".workbuddy" / "skills" / "wechat-ai-publisher",
    ]
    for c in cands:
        if (c / "scripts" / "publish_gzh.py").is_file():
            return c
    sys.exit("缺少依赖技能 wechat-ai-publisher：先 `skillhub install wechat-ai-publisher`，"
             "或在 config.json 的 paths.publisher_skill 里填它的安装路径。")


SKILL = _resolve_publisher_skill(CFG["paths"].get("publisher_skill"))

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_assets  # noqa: E402


def run_cmd(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, encoding="utf-8")
    print(r.stdout[-800:] if len(r.stdout) > 800 else r.stdout)
    if r.returncode != 0:
        print("ERR:", r.stderr[-800:] if len(r.stderr) > 800 else r.stderr, file=sys.stderr)
        if check:
            sys.exit(r.returncode)
    return r


def md_to_html(md_path: Path, out_html: Path, theme=""):
    cmd = [
        PY, str(SKILL / "scripts" / "markdown_to_wechat_doocs.py"),
        "--input", str(md_path),
        "--output", str(out_html),
    ]
    if theme:
        cmd += ["--theme", theme]
    run_cmd(cmd)
    print(f"[md→html] {out_html}")


def find_cover(slug_dir: Path):
    candidates = ["封面-900x383.png", "cover.png", "封面.png"]
    for c in candidates:
        p = slug_dir / c
        if p.exists():
            return p
    raise SystemExit(f"找不到封面图，请在 {slug_dir} 放 封面-900x383.png")


def extract_title(md_path: Path):
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r"^# (.+)$", text, re.M)
    return m.group(1).strip() if m else "未命名"


def extract_digest(md_path: Path, max_len=50):
    text = md_path.read_text(encoding="utf-8")
    # 取第一个非空非标题、非引用、非分割线的段落
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith(("#", ">", "---", "!", "-", "*")):
            # 清掉 Markdown 标记符号
            line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            line = re.sub(r"\*(.+?)\*", r"\1", line)
            line = re.sub(r"`(.+?)`", r"\1", line)
            return line[:max_len]
    return ""


def publish(html_path: Path, cover_path: Path, title: str, author: str, digest: str,
            out_dir: Path, dry_run: bool):
    cmd = [
        PY, str(SKILL / "scripts" / "publish_gzh.py"),
        "--html", str(html_path),
        "--cover", str(cover_path),
        "--title", title,
        "--author", author,
        "--digest", digest,
        "--out-dir", str(out_dir),
    ]
    if dry_run:
        cmd.append("--dry-run")
    run_cmd(cmd)
    print(f"[publish] {'(dry-run)' if dry_run else 'done'} title={title}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article", required=True, help="输入 Markdown 文件路径")
    ap.add_argument("--slug", default="", help="日期/目录名，如 20261023；留空从文件名提取")
    ap.add_argument("--theme", default="", help="doocs 主题: cyan/orange/green/purple/default")
    ap.add_argument("--author", default=CFG["brand"]["name"])
    ap.add_argument("--assets", default="",
                    help="素材清单 JSON；默认与文章同名 <article>.assets.json")
    ap.add_argument("--dry-run", action="store_true",
                    help="预演：不联网、不写 articles/published，产物留 .build/<slug>/preview/")
    a = ap.parse_args()

    md_path = Path(a.article).resolve()
    slug = a.slug or re.sub(r"^\d{8}-", "", md_path.stem)[:8]
    if not re.match(r"^\d{8}$", slug):
        slug = datetime.now().strftime("%Y%m%d")

    pic_dir = Path(CFG["paths"]["pic_root"]) / slug
    published_dir = Path(CFG["paths"]["article_published"])
    build_root = Path(CFG["paths"]["build"]) / slug
    if a.dry_run:
        # dry-run 全部产物收敛到 .build/<slug>/preview/，不碰 published
        build_dir = build_root / "preview"
        build_dir.mkdir(parents=True, exist_ok=True)
    else:
        build_dir = build_root
        build_dir.mkdir(parents=True, exist_ok=True)
        published_dir.mkdir(parents=True, exist_ok=True)

    cover = find_cover(pic_dir)
    title = extract_title(md_path)
    digest = extract_digest(md_path)

    print(f"== 流水线开始 ==")
    print(f"  文章: {md_path}")
    print(f"  slug: {slug}")
    print(f"  封面: {cover}")
    print(f"  标题: {title}")
    print(f"  摘要: {digest}")
    print(f"  作者: {a.author}")
    print(f"  模式: {'dry-run（预览目录 %s）' % build_dir if a.dry_run else '正式发布'}")

    # ── 1. 素材清单门禁（上传前，离线）────────────────────
    try:
        ok, rep = check_assets.run_check(md_path, a.assets)
    except check_assets.AssetError as e:
        print(f"❌ 素材门禁阻断：\n{e}", file=sys.stderr)
        sys.exit(1)
    if not ok:
        print("❌ 素材门禁阻断，问题如下；修复前不转换、不上传。", file=sys.stderr)
        for p in rep["problems"]:
            print("  - %s" % p, file=sys.stderr)
        sys.exit(1)

    # ── 2. Markdown → HTML ────────────────────────────────
    html_path = build_dir / f"{slug}.html"
    md_to_html(md_path, html_path, a.theme)

    # ── 3. HTML 引用复核 + 落检查报告（仍在上传前）─────────
    report_path = build_dir / "assets-report.json"
    ok, rep = check_assets.run_check(md_path, a.assets, html=str(html_path),
                                     report=str(report_path))
    if not ok:
        print("❌ HTML 引用复核未过，发布前检查失败：", file=sys.stderr)
        for p in rep["problems"]:
            print("  - %s" % p, file=sys.stderr)
        sys.exit(1)
    print(f"[assets] 门禁通过，报告：{report_path}")

    # ── 4. 发布（dry-run 不联网）──────────────────────────
    publish(html_path, cover, title, a.author, digest, published_dir, a.dry_run)

    # ── 5. 归档（仅正式发布；dry-run 不写 published）───────
    if not a.dry_run:
        archive_md = published_dir / f"{slug}_{md_path.name}"
        archive_md.write_bytes(md_path.read_bytes())
        print(f"[archive] {archive_md}")
    else:
        print(f"[dry-run] 未写入 articles/published；预览：{html_path}")
    print("== 完成 ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
