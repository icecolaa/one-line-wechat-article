#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
素材清单门禁（离线，不联网）

清单默认与文章同名：<article>.assets.json（可用 --assets 覆盖）。
schema 见 WORKFLOW.md「素材清单 schema」一节，要点：
  - images[]: 逐图登记；required=true 的图片缺文件、未在正文引用、
    hash/尺寸与登记不符，或图注未出现在正文，都会阻断。
  - cover:   只查存在与 hash，不进正文引用。
  - 正文引用了清单之外的本地图片 → 阻断；正文引用的本地图片不存在 → 阻断。
  - 传入 --html 时追加检查：每张 required 图片必须出现在 HTML 的 <img src> 中，
    HTML 中的本地图片路径必须存在。

用法：
    python pipeline/check_assets.py --article articles/src/20261023-开篇自述.md
    python pipeline/check_assets.py --article ... --html .build/20261023/preview/20261023.html \
        --report .build/20261023/preview/assets-report.json

退出码：0 = 全部通过；1 = 阻断（问题逐条打印）。
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# Windows 控制台中文兼容
if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

WECHAT_DOMAINS = ("mmbiz.qpic.cn", "qpic.cn")
MD_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HTML_IMG_SRC_RE = re.compile(r"<img[^>]+src=\"([^\"]+)\"")

MANIFEST_TEMPLATE = """{
  "schema_version": 1,
  "slug": "YYYYMMDD",
  "article": "<文章 Markdown 绝对路径，正斜杠>",
  "cover": {
    "file": "<封面绝对路径，正斜杠>",
    "required": true,
    "kind": "cover",
    "sha256": "<封面文件 SHA256>",
    "width": 900,
    "height": 383,
    "usage": "头条封面 2.35:1"
  },
  "images": [
    {
      "id": "gotrip-01-overview",
      "file": "<图片绝对路径，正斜杠>",
      "required": true,
      "kind": "screenshot-miniprogram",
      "source": {
        "type": "screenshot",
        "path": "<原图绝对路径，正斜杠>",
        "env": "来源页面/环境（如：小程序开发版本，未提审）",
        "data": "数据性质（如：演示数据）",
        "sha256": "<原图 SHA256>",
        "note": "原样复制，未缩放/裁切/重编码"
      },
      "usage": "用途与目标段落",
      "caption": "正文图注（须与 Markdown ![alt] 一致）",
      "sha256": "<文件 SHA256>",
      "width": 774,
      "height": 1578
    }
  ]
}"""


class AssetError(Exception):
    """素材门禁阻断。"""


def norm(p: str) -> str:
    """统一为绝对、正斜杠路径，便于逐字符比对。"""
    return Path(os.path.expanduser(str(p))).resolve().as_posix()


def is_local(src: str) -> bool:
    s = str(src)
    if s.startswith(("http://", "https://", "data:")):
        return False
    if any(d in s for d in WECHAT_DOMAINS):
        return False
    return True


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_size(path: Path):
    """返回 (w, h)；PIL 不可用时返回 None（跳过尺寸校验）。"""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


def md_image_refs(md_text: str):
    """[(alt, 原始路径)]，保持出现顺序。"""
    return [(m.group(1), m.group(2)) for m in MD_IMG_RE.finditer(md_text)]


def html_img_srcs(html_text: str):
    return HTML_IMG_SRC_RE.findall(html_text)


def default_manifest_path(article: Path) -> Path:
    return article.with_suffix(".assets.json")


def load_manifest(article: Path, assets: str = "") -> dict:
    """读取并做 schema 自检；缺清单/坏清单直接阻断并给可执行提示。"""
    mpath = Path(assets).resolve() if assets else default_manifest_path(article)
    if not mpath.is_file():
        raise AssetError(
            "找不到素材清单：%s\n"
            "每篇文章都必须有一份逐图素材清单（默认与文章同名：%s）。\n"
            "请新建该文件，最小模板：\n%s"
            % (mpath, default_manifest_path(article).name, MANIFEST_TEMPLATE)
        )
    try:
        data = json.loads(mpath.read_text(encoding="utf-8"))
    except Exception as e:
        raise AssetError("素材清单不是合法 JSON：%s（%s）" % (mpath, e))
    if not isinstance(data, dict) or not isinstance(data.get("images"), list):
        raise AssetError(
            "素材清单缺少 images 数组：%s\n请参考模板补全：\n%s" % (mpath, MANIFEST_TEMPLATE)
        )
    for i, img in enumerate(data["images"]):
        for key in ("id", "file", "required", "sha256", "caption"):
            if key not in img:
                raise AssetError("素材清单 images[%d] 缺少字段 %s：%s" % (i, key, mpath))
    return data


def check_stage_md(manifest: dict, md_path: Path):
    """上传前检查（只依赖 Markdown + 清单 + 图片文件）。返回 (problems, rows)。"""
    problems = []
    rows = []
    md_text = md_path.read_text(encoding="utf-8")
    refs = md_image_refs(md_text)
    ref_paths = [norm(p) for _, p in refs]

    # 封面：存在 + hash（不进正文引用）
    cover = manifest.get("cover") or {}
    cover_row = None
    if cover.get("required"):
        cf = Path(cover["file"])
        cover_row = {"id": "cover", "file": norm(cover["file"]), "exists": cf.is_file(),
                     "sha256_ok": None, "referenced_in_md": None, "in_html": None}
        if not cf.is_file():
            problems.append("[cover] 封面不存在：%s" % cover["file"])
        else:
            got = sha256_of(cf)
            cover_row["sha256_ok"] = (not cover.get("sha256")) or got.lower() == str(cover["sha256"]).lower()
            if not cover_row["sha256_ok"]:
                problems.append("[cover] 封面 hash 与清单不符：%s" % cover["file"])

    # 逐图：存在 / hash / 尺寸 / 正文引用 / 图注
    for img in manifest["images"]:
        if not img.get("required"):
            continue
        fid = img.get("id", img["file"])
        f = Path(img["file"])
        row = {"id": fid, "file": norm(img["file"]), "exists": f.is_file(),
               "sha256_ok": None, "size_ok": None, "referenced_in_md": None,
               "caption_ok": None}
        if not f.is_file():
            problems.append("[%s] 图片不存在：%s" % (fid, img["file"]))
            rows.append(row)
            continue
        got = sha256_of(f)
        row["sha256_ok"] = (not img.get("sha256")) or got.lower() == str(img["sha256"]).lower()
        if not row["sha256_ok"]:
            problems.append("[%s] 图片 hash 与清单不符（被改动过？）：%s" % (fid, img["file"]))
        size = image_size(f)
        if size and img.get("width") and img.get("height"):
            row["size_ok"] = size == (int(img["width"]), int(img["height"]))
            if not row["size_ok"]:
                problems.append(
                    "[%s] 图片尺寸与清单不符：实际 %s，清单 %sx%s（%s）"
                    % (fid, size, img["width"], img["height"], img["file"]))
        row["referenced_in_md"] = norm(img["file"]) in ref_paths
        if not row["referenced_in_md"]:
            problems.append("[%s] 必需图片未在正文引用：%s" % (fid, img["file"]))
        cap = (img.get("caption") or "").strip()
        if cap:
            matching_alts = [alt for alt, src in refs if norm(src) == norm(img["file"])]
            row["caption_ok"] = bool(matching_alts) and all(alt == cap for alt in matching_alts)
            if not row["caption_ok"]:
                problems.append("[%s] 图注与该图片的 Markdown ![alt] 不一致：%s" % (fid, cap))
        rows.append(row)

    # 正文全部本地图片：必须存在 + 必须登记在清单
    declared = {norm(i["file"]) for i in manifest["images"]}
    for alt, src in refs:
        if not is_local(src):
            continue
        nsrc = norm(src)
        if not Path(nsrc).is_file():
            problems.append("[md] 正文引用的本地图片不存在：%s（alt=%s）" % (src, alt))
        if nsrc not in declared:
            problems.append(
                "[md] 正文引用了清单之外的本地图片：%s\n"
                "     请把它登记进 %s 的 images[]，或改成微信域/外链。" % (src, default_manifest_path(md_path)))
    return problems, rows, cover_row


def check_stage_html(manifest: dict, html_path: Path):
    """生成 HTML 后检查：required 图片必须进入 HTML；HTML 本地图片必须存在。"""
    problems = []
    html_text = html_path.read_text(encoding="utf-8")
    srcs = html_img_srcs(html_text)
    src_norms = {norm(s) for s in srcs if is_local(s)}
    for img in manifest["images"]:
        if not img.get("required"):
            continue
        if norm(img["file"]) not in src_norms:
            problems.append("[%s] 必需图片未进入 HTML：%s" % (img.get("id"), img["file"]))
    for s in srcs:
        if is_local(s) and not Path(norm(s)).is_file():
            problems.append("[html] HTML 引用的本地图片不存在：%s" % s)
    return problems, {"html": norm(html_path), "img_srcs": len(srcs)}


def run_check(article: Path, assets: str = "", html: str = "", report: str = ""):
    """执行门禁；返回 (ok, report_dict)。"""
    manifest = load_manifest(article, assets)
    problems, rows, cover_row = check_stage_md(manifest, article)
    html_info = None
    if html:
        html_path = Path(html)
        if not html_path.is_file():
            problems.append("[html] 找不到待检查 HTML：%s" % html)
        else:
            hproblems, html_info = check_stage_html(manifest, html_path)
            problems.extend(hproblems)
    report_data = {
        "article": norm(article),
        "manifest": norm(Path(assets).resolve() if assets else default_manifest_path(article)),
        "html": norm(html) if html else None,
        "ok": not problems,
        "cover": cover_row,
        "images": rows,
        "problems": problems,
    }
    if report:
        rp = Path(report)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return (not problems), report_data


def main():
    ap = argparse.ArgumentParser(description="素材清单门禁（离线）")
    ap.add_argument("--article", required=True, help="文章 Markdown 路径")
    ap.add_argument("--assets", default="", help="素材清单 JSON；默认与文章同名 .assets.json")
    ap.add_argument("--html", default="", help="生成后的 HTML；提供则追加 HTML 引用检查")
    ap.add_argument("--report", default="", help="检查报告输出路径（JSON）")
    a = ap.parse_args()

    try:
        ok, rep = run_check(Path(a.article), a.assets, a.html, a.report)
    except AssetError as e:
        print("❌ 素材门禁阻断：\n%s" % e, file=sys.stderr)
        return 1

    if rep.get("cover"):
        c = rep["cover"]
        print("· %(id)s 存在=%(exists)s hash=%(sha256_ok)s（封面，不进正文）"
              % dict(c, exists=c.get("exists"), sha256_ok=c.get("sha256_ok")))
    for row in rep["images"]:
        print("· %(id)s 存在=%(exists)s hash=%(sha256_ok)s 正文引用=%(referenced_in_md)s 图注=%(caption_ok)s"
              % dict(row, exists=row.get("exists"), sha256_ok=row.get("sha256_ok"),
                     referenced_in_md=row.get("referenced_in_md"), caption_ok=row.get("caption_ok")))
    if a.report:
        print("报告：%s" % a.report)
    if ok:
        print("✅ 素材门禁通过：%d 张必需图片全部存在、已引用、hash/图注一致" % len(rep["images"]))
        return 0
    print("❌ 素材门禁阻断，共 %d 个问题：" % len(rep["problems"]), file=sys.stderr)
    for p in rep["problems"]:
        print("  - %s" % p, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
