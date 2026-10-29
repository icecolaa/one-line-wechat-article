---
name: one-line-wechat-article
slug: one-line-wechat-article
version: 1.0.0
displayName: 一句话生成公众号文章
display_name: 一句话生成公众号文章
display_name_en: One-Line WeChat Article
description: 一句话主题（可选配一批真实截图）→ 排版成稿 + 封面/分享图 + 逐图素材门禁 → 公众号草稿箱 + 归档的全流程 skill。复制一句开场白就能开工，不用记参数。内含 9 套精确像素封面/分享图模板（HTML 截屏，中文一个不差）、逐图素材清单门禁（缺图/未引用/hash/图注不符即阻断，附 13 项离线回归测试）、一条龙发布器与素材脚手架。文风四规则（短句一句一事、主谓相邻、不堆名词、不自造比喻）与图注必须以实际截图为准的验收法写在 references/ 里。什么时候用：给公众号写连载/单篇、要把截图素材变成图文草稿、要给文章配封面和分享图、要在发布前做逐图验收。不用于：多源深度调研、海报平面设计、视频号内容。依赖：skillhub 技能 wechat-ai-publisher（排版转 HTML 与建草稿）、本机 Chrome/Edge、Python + Pillow。
description_zh: "一句话主题 + 可选截图 → 文章骨架 → 逐图门禁 → 封面/分享图 → 排版 → 草稿箱 + 归档。9 套精确像素模板，13 项离线回归测试，文风四规则内置。"
description_en: "One-line topic plus optional real screenshots → article skeleton → per-image gate → cover/share posters → WeChat formatting → draft box + archive. 9 pixel-exact templates, 13 offline regression tests, built-in style rules."
tags: ["wechat", "公众号", "写作", "排版", "封面", "门禁"]
license: MIT
homepage: https://skillhub.cn/skills/one-line-wechat-article
---

# 一句话生成公众号文章

一句话：**主题 → 成稿 → 配图 → 门禁 → 草稿箱 → 归档**，每一步都有脚本和门禁兜底。

## 8 句可直接复制的开场白

复制任意一句给 AI，就能开工：

1. 「用一句话主题帮我写一篇公众号文章并存草稿箱：主题是____」
2. 「我有一批截图在____目录，围绕主题____写篇文章，截图全部用上」
3. 「今天这篇的主题是____，按系列第 N 篇写，结尾预告下一篇」
4. 「帮我把____目录里的截图逐张核实，写成图文稿，图注以截图为准」
5. 「给主题____写文章，标题按爆款钩子给 6 个候选让我选」
6. 「只走预演不要发：主题____，产出预览 HTML 给我看」
7. 「检查现有稿子的素材门禁，列出问题并修」
8. 「给这段旅行/项目截图配一套封面加 5:4 分享图」

## 什么时候用我 / 什么时候别用我

**用我**：公众号连载或单篇成稿；截图素材变图文；封面 900×383 与分享图 1200×960 两件套；发布前逐图验收；只预演不发布。

**别用我**：多源深度调研、带引用的研究报告、平面海报设计、视频号内容。纯排版发布（已有排版 HTML）可以直接用依赖技能 wechat-ai-publisher。

## 依赖（先装好再开工）

1. **wechat-ai-publisher** 技能：`skillhub install wechat-ai-publisher`。负责 Markdown→微信 HTML、上传素材、建草稿。公众号凭证配在它的 `.env`（本 skill 不读取、不输出任何密钥）。
2. **Chrome 或 Edge**（无头截屏用），以及 **Python 3.8+**（`pip install pillow markdown requests`）。
3. 在**项目根目录**运行本 skill 的脚本（相对路径 `pic/`、`articles/`、`.build/` 都解析到当前目录）。

## 流程（六步，每步有门禁）

```
① 开稿脚手架 → ② 按一句话写正文 → ③ 素材逐图核实+回填清单
→ ④ 封面/分享图 → ⑤ 离线门禁+预演 → ⑥ 建草稿+归档
```

**① 开稿**（搭目录、骨架、清单，一步到位）：

```powershell
python <本skill>/scripts/new_article.py --topic "旅行 App 越做越复杂，你还是用回了备忘录" --slug 20261101 --images E:\path\截图目录
```

**② 写正文**：AI 按骨架注释和 `references/style-rules.md`（四条文风规则）成稿。图片用**绝对正斜杠路径**插进正文；图注写在 `![ ]` 里，必须与截图画面一致。

**③ 逐图核实**：每张截图必须亲眼看过原图再写图注。数字、日期、页面身份写进图注前，先在原图上看到。素材清单 `<文章名>.assets.json` 逐图登记 sha256/尺寸/来源/图注——**缺一张、未引用、hash 不符、图注与正文不一致都会阻断**（`scripts/check_assets.py`，13 项离线回归测试兜底）。

**④ 配图两件套**（HTML 模板截屏，中文字一个不差）：

```powershell
python <本skill>/scripts/build.py cover-shot --art1 a.png --art2 b.png --out pic/<slug>/封面-900x383.png --h1 "大标题" --badge "连载 · 第 N 篇"
python <本skill>/scripts/build.py share-poster --art1 a.png --art2 b.png --art3 c.png --out pic/<slug>/分享图-5x4.png --h1 "大标题" --serial N
```

生成后把封面路径与 sha256 回填进素材清单的 `cover` 字段。

**⑤ 门禁 + 预演**（不联网、不写归档）：

```powershell
python <本skill>/scripts/check_assets.py --article <md 路径>
python <本skill>/scripts/run.py --article <md 路径> --slug <slug> --theme cyan --dry-run
```

**⑥ 建草稿 + 归档**（去掉 `--dry-run`）：草稿进公众号草稿箱，HTML+meta 归档到 `articles/published/`。群发必须在公众号后台人工确认。

## 截图换新了怎么办

源截图是唯一真相。截图目录一变，所有引用它的图注视为失效：重新复制、重算 hash、逐张重看、回填清单，再走 ⑤⑥。已发布的草稿用依赖技能的 `update_draft.py`（建新→删旧）更新。

## 本地自检

```powershell
python -m unittest discover -s <本skill>/scripts/tests -v   # 13 项离线回归
```

## 目录结构

```
scripts/
  new_article.py     ① 开稿脚手架（目录+骨架+清单）
  check_assets.py    ③ 逐图素材门禁（离线）
  build.py           ④ 封面/分享图/插图合成（HTML→精确像素 PNG）
  run.py             ⑤⑥ 一条龙：门禁→排版→建草稿→归档
  tools/shot.py      Chrome 无头精确截屏
  templates/         9 套封面/分享图/插图 HTML 模板
  tests/             13 项离线回归测试
  config.json        相对路径 + 尺寸 + 品牌信息（在项目根目录解析）
references/
  style-rules.md     文风四规则与改写示例
  assets-schema.md   素材清单逐字段说明
```
