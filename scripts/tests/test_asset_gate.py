# -*- coding: utf-8 -*-
"""
素材门禁离线回归测试（不联网）

覆盖：
  1. 完整清单通过（md 阶段 + html 阶段）
  2. 必需图片文件缺失 → 阻断
  3. 必需图片未在正文引用 → 阻断
  4. 正文引用不存在的本地图片 → 阻断
  5. 正文引用清单之外的本地图片 → 阻断
  6. 图注与正文 alt 不一致 → 阻断
  7. 图片 hash 被改动 → 阻断
  8. required 图片未进入 HTML → 阻断
  9. 缺素材清单 → 阻断（且提示可执行）
 10. dry-run 端到端：退出 0、articles/published 不变、预览落在 .build/<slug>/preview/

运行：
    python -m unittest discover -s <skill>/scripts/tests -v
"""
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import check_assets  # noqa: E402

# 1x1 透明 PNG，测试夹具用，避免依赖 PIL 造图
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class AssetGateTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ep1-assets-test-"))
        self.md = self.tmp / "20260101-测试文章.md"
        self.assets = self.tmp / "20260101-测试文章.assets.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_png(self, name: str, data: bytes = PNG_1X1) -> Path:
        p = self.tmp / name
        p.write_bytes(data)
        return p

    def write_manifest(self, images, cover=None):
        data = {"schema_version": 1, "slug": "20260101",
                "article": self.md.as_posix(), "images": images}
        if cover:
            data["cover"] = cover
        self.assets.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def img_entry(self, path: Path, caption="测试图注", img_id="img-1"):
        return {
            "id": img_id,
            "file": path.as_posix(),
            "required": True,
            "kind": "screenshot-miniprogram",
            "source": {"type": "screenshot", "path": path.as_posix(),
                       "env": "测试环境", "data": "演示数据",
                       "sha256": sha256_bytes(path.read_bytes())},
            "usage": "测试用途",
            "caption": caption,
            "sha256": sha256_bytes(path.read_bytes()),
            "width": 1, "height": 1,
        }


class TestFullManifestPasses(AssetGateTestBase):
    def test_md_stage_and_html_stage_pass(self):
        p1 = self.write_png("a.png")
        p2 = self.write_png("b.png")
        self.md.write_text(
            "# 标题\n\n![测试图注]({a})\n\n正文\n\n![第二张]({b})\n".format(a=p1.as_posix(), b=p2.as_posix()),
            encoding="utf-8")
        e2 = self.img_entry(p2, caption="第二张", img_id="img-2")
        self.write_manifest([self.img_entry(p1), e2],
                            cover={"file": p1.as_posix(), "required": True,
                                   "sha256": sha256_bytes(PNG_1X1), "width": 1, "height": 1})
        ok, rep = check_assets.run_check(self.md)
        self.assertTrue(ok, rep["problems"])

        html = self.tmp / "out.html"
        html.write_text('<section><img src="{a}" alt="测试图注" /><img src="{b}" alt="第二张" /></section>'
                        .format(a=p1.as_posix(), b=p2.as_posix()), encoding="utf-8")
        ok, rep = check_assets.run_check(self.md, html=str(html))
        self.assertTrue(ok, rep["problems"])


class TestBlockingCases(AssetGateTestBase):
    def _base(self):
        p1 = self.write_png("a.png")
        p2 = self.write_png("b.png")
        self.md.write_text(
            "# 标题\n\n![测试图注]({a})\n\n正文\n".format(a=p1.as_posix()), encoding="utf-8")
        return p1, p2

    def test_missing_required_file_blocks(self):
        p1, _ = self._base()
        ghost = self.tmp / "gone.png"  # 清单登记了，但文件不在磁盘上
        entry = self.img_entry(p1)
        entry2 = dict(entry, id="img-2", file=ghost.as_posix(),
                      sha256=sha256_bytes(PNG_1X1))
        self.write_manifest([entry, entry2])
        ok, rep = check_assets.run_check(self.md)
        self.assertFalse(ok)
        self.assertTrue(any("不存在" in p for p in rep["problems"]))

    def test_unreferenced_required_image_blocks(self):
        p1, p2 = self._base()
        self.write_manifest([self.img_entry(p1), self.img_entry(p2, img_id="img-2")])
        self.md.write_text("# 标题\n\n![测试图注]({a})\n".format(a=p1.as_posix()), encoding="utf-8")
        ok, rep = check_assets.run_check(self.md)
        self.assertFalse(ok)
        self.assertTrue(any("未在正文引用" in p for p in rep["problems"]))

    def test_md_references_missing_file_blocks(self):
        p1, _ = self._base()
        ghost = (self.tmp / "ghost.png").as_posix()
        self.md.write_text("# 标题\n\n![测试图注]({a})\n\n![鬼图]({g})\n".format(a=p1.as_posix(), g=ghost),
                           encoding="utf-8")
        self.write_manifest([self.img_entry(p1)])
        ok, rep = check_assets.run_check(self.md)
        self.assertFalse(ok)
        self.assertTrue(any("不存在" in p for p in rep["problems"]))

    def test_undeclared_reference_blocks(self):
        p1, p2 = self._base()
        self.md.write_text("# 标题\n\n![测试图注]({a})\n\n![第二张]({b})\n"
                           .format(a=p1.as_posix(), b=p2.as_posix()), encoding="utf-8")
        self.write_manifest([self.img_entry(p1)])  # p2 未登记
        ok, rep = check_assets.run_check(self.md)
        self.assertFalse(ok)
        self.assertTrue(any("清单之外" in p for p in rep["problems"]))

    def test_caption_mismatch_blocks(self):
        p1, _ = self._base()
        self.md.write_text("# 标题\n\n![另一句]({a})\n".format(a=p1.as_posix()), encoding="utf-8")
        self.write_manifest([self.img_entry(p1, caption="测试图注")])
        ok, rep = check_assets.run_check(self.md)
        self.assertFalse(ok)
        self.assertTrue(any("图注" in p for p in rep["problems"]))

    def test_hash_drift_blocks(self):
        p1, _ = self._base()
        self.write_manifest([self.img_entry(p1)])
        p1.write_bytes(PNG_1X1 + b"\x00tampered")  # 内容被改动
        ok, rep = check_assets.run_check(self.md)
        self.assertFalse(ok)
        self.assertTrue(any("hash" in p for p in rep["problems"]))

    def test_caption_elsewhere_cannot_mask_wrong_image_alt(self):
        p1, p2 = self._base()
        self.md.write_text(
            "# 标题\n\n测试图注\n\n![错误图注]({a})\n\n![测试图注]({b})\n".format(
                a=p1.as_posix(), b=p2.as_posix()), encoding="utf-8")
        self.write_manifest([self.img_entry(p1), self.img_entry(p2, img_id="img-2")])
        ok, rep = check_assets.run_check(self.md)
        self.assertFalse(ok)
        self.assertFalse(rep["images"][0]["caption_ok"])
        self.assertTrue(rep["images"][1]["caption_ok"])

    def test_cover_hash_drift_is_reported_false(self):
        p1, p2 = self._base()
        self.write_manifest([self.img_entry(p1)], cover={
            "file": p2.as_posix(), "required": True, "sha256": sha256_bytes(PNG_1X1)})
        p2.write_bytes(PNG_1X1 + b"tampered")
        ok, rep = check_assets.run_check(self.md)
        self.assertFalse(ok)
        self.assertTrue(rep["cover"]["exists"])
        self.assertFalse(rep["cover"]["sha256_ok"])

    def test_missing_cover_has_failed_report_row(self):
        p1, _ = self._base()
        self.write_manifest([self.img_entry(p1)], cover={
            "file": (self.tmp / "missing-cover.png").as_posix(), "required": True,
            "sha256": sha256_bytes(PNG_1X1)})
        ok, rep = check_assets.run_check(self.md)
        self.assertFalse(ok)
        self.assertFalse(rep["cover"]["exists"])
        self.assertIsNone(rep["cover"]["sha256_ok"])

    def test_required_image_missing_in_html_blocks(self):
        p1, _ = self._base()
        self.write_manifest([self.img_entry(p1)])
        ok, _ = check_assets.run_check(self.md)
        self.assertTrue(ok)
        html = self.tmp / "out.html"
        html.write_text('<section><p>没有图</p></section>', encoding="utf-8")
        ok, rep = check_assets.run_check(self.md, html=str(html))
        self.assertFalse(ok)
        self.assertTrue(any("未进入 HTML" in p for p in rep["problems"]))

    def test_missing_manifest_blocks_with_hint(self):
        p1, _ = self._base()
        # 不写清单
        with self.assertRaises(check_assets.AssetError) as ctx:
            check_assets.run_check(self.md)
        self.assertIn("assets.json", str(ctx.exception))


class TestDryRunEndToEnd(unittest.TestCase):
    """在临时项目里跑端到端 dry-run：退出 0、published 不变、预览落 preview/。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ep-dryrun-test-"))
        self.published = self.tmp / "articles" / "published"
        self.published.mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dry_run_end_to_end(self):
        # 依赖技能/库不可用时跳过（dry-run 需要它们排版 HTML）
        try:
            import importlib
            spec_ok = any((Path.home() / sub / "wechat-ai-publisher" / "scripts"
                           / "markdown_to_wechat_doocs.py").is_file()
                          for sub in (".workbuddy-ai/skills", ".zcode/skills",
                                      ".workbuddy/skills"))
            importlib.import_module("markdown")
        except Exception:
            self.skipTest("缺少 wechat-ai-publisher 或 markdown 依赖")
        self.assertTrue(spec_ok, "缺少 wechat-ai-publisher")

        img = self.tmp / "a.png"
        img.write_bytes(PNG_1X1)
        cover = self.tmp / "pic" / "20260101" / "封面-900x383.png"
        cover.parent.mkdir(parents=True)
        cover.write_bytes(PNG_1X1)
        article = self.tmp / "articles" / "src" / "20260101-测试.md"
        article.parent.mkdir(parents=True)
        manifest = {"schema_version": 1, "slug": "20260101",
                    "article": article.as_posix(),
                    "cover": {"file": cover.as_posix(), "required": True,
                              "sha256": sha256_bytes(PNG_1X1), "width": 900, "height": 383},
                    "images": [{
                        "id": "img-1", "file": img.as_posix(), "required": True,
                        "kind": "screenshot",
                        "source": {"type": "screenshot", "path": img.as_posix(),
                                   "env": "测试", "data": "演示",
                                   "sha256": sha256_bytes(PNG_1X1)},
                        "usage": "测试", "caption": "测试图注",
                        "sha256": sha256_bytes(PNG_1X1), "width": 1, "height": 1}]}
        article.write_text("# 标题" + chr(10)*2 + "![测试图注](" + img.as_posix() + ")" + chr(10)*2 + "正文" + chr(10), encoding="utf-8")
        (article.parent / "20260101-测试.assets.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "run.py"),
             "--article", str(article), "--slug", "20260101",
             "--theme", "cyan", "--dry-run"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(self.tmp))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

        self.assertEqual(list(self.published.iterdir()), [], "dry-run 改动了 articles/published")
        preview_dir = self.tmp / ".build" / "20260101" / "preview"
        html = preview_dir / "20260101.html"
        self.assertTrue(html.is_file(), "dry-run 预览 HTML 未落在 .build/<slug>/preview/")
        self.assertIn("a.png", html.read_text(encoding="utf-8"), "预览 HTML 缺少图片")
        report = preview_dir / "assets-report.json"
        self.assertTrue(report.is_file(), "缺少素材检查报告")
        rep = json.loads(report.read_text(encoding="utf-8"))
        self.assertTrue(rep["ok"], rep["problems"])
        self.assertIsNotNone(rep.get("cover"), "封面应单独登记")


if __name__ == "__main__":
    unittest.main(verbosity=2)
