# 素材清单 schema（`<文章名>.assets.json`）

清单与文章同名、同目录。缺清单、缺图、未引用、hash/尺寸/图注不符，都会在发布前阻断。

```jsonc
{
  "schema_version": 1,
  "slug": "20261101",
  "article": "articles/src/20261101-示例.md",   // 绝对正斜杠路径
  "cover": {
    "file": "pic/20261101/封面-900x383.png",    // 生成后回填
    "required": true,
    "kind": "cover",
    "sha256": "<文件 SHA256>",
    "width": 900,
    "height": 383,
    "usage": "头条封面 2.35:1"
  },
  "images": [
    {
      "id": "img-xxx",                          // 唯一 id
      "file": "<图片绝对正斜杠路径>",
      "required": true,
      "kind": "screenshot",                     // screenshot / cover / 插画
      "source": {
        "type": "screenshot",
        "path": "<原图路径>",                    // 源目录是唯一真相
        "env": "来源页面/环境（如：小程序开发版，未提审）",
        "data": "数据性质（真实数据 / 演示数据）",
        "sha256": "<原图 SHA256>",
        "note": "原样复制，未缩放/裁切/重编码"
      },
      "usage": "用在哪一节、回答什么问题",
      "caption": "正文图注（必须与 ![ ] 内文字逐字一致）",
      "sha256": "<副本 SHA256>",
      "width": 1290,
      "height": 2796
    }
  ],
  "share": {                                    // 可选，留痕不校验
    "file": "pic/20261101/分享图-5x4.png",
    "sha256": "...", "width": 1200, "height": 960,
    "usage": "5:4 分享海报"
  }
}
```

## 门禁规则（check_assets.py，离线）

每张 `required` 图片查六项：文件存在、SHA256 一致、尺寸一致、正文引用、图注一致、（带 `--html` 时）进入 HTML。另有两类反向拦截：正文引用了清单之外的本地图片 → 阻断；正文引用的本地图片不存在 → 阻断。

## 运维要点

- 源截图目录是唯一真相。截图重拍后：重新复制 → 重算 hash → 逐张重看 → 回填 caption → 重跑门禁。
- 同内容不同名的重复图按 hash 去重，只保留一份；同一文件在正文里只引用一次（同图异注会被拦）。
- 常用命令：

```powershell
# 单独跑门禁
python <skill>/scripts/check_assets.py --article <md路径> --html <html路径> --report <报告路径>

# 13 项离线回归测试
python -m unittest discover -s <skill>/scripts/tests -v
```
