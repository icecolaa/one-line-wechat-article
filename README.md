# one-line-wechat-article · 一句话生成公众号文章

一句话主题（可选配一批真实截图）→ 排版成稿 + 封面/分享图 + 逐图素材门禁 → 公众号草稿箱 + 归档。

这是 [SkillHub](https://skillhub.cn/skills/one-line-wechat-article) 上的技能源码仓库。完整说明见 [SKILL.md](SKILL.md)。

## 快速开始

```powershell
# 0. 依赖
skillhub install wechat-ai-publisher   # 排版 + 建草稿（凭证配在它自己的 .env）
pip install pillow markdown requests   # Python 依赖

# 1. 开稿（在项目根目录运行；目录会自动创建）
python <本仓库>/scripts/new_article.py --topic "你的主题一句话" --slug 20261101 --images E:\path\截图目录

# 2. 写正文（AI 按 references/style-rules.md 的四条文风规则写）
#    图片用绝对正斜杠路径插进正文，图注写在 ![ ] 里

# 3. 门禁 + 预演（不联网）
python <本仓库>/scripts/check_assets.py --article articles/src/xxx.md
python <本仓库>/scripts/run.py --article articles/src/xxx.md --slug 20261101 --theme cyan --dry-run

# 4. 建草稿（去掉 --dry-run；群发在公众号后台人工确认）
python <本仓库>/scripts/run.py --article articles/src/xxx.md --slug 20261101 --theme cyan
```

## 亮点

- **逐图素材门禁**：每张截图登记 sha256/尺寸/来源/图注；缺图、未引用、hash 漂移、图注与正文不一致都发布前阻断，附 13 项离线回归测试。
- **精确像素配图**：封面 900×383、分享图 1200×960、插图 1080×720 共 9 套 HTML 模板，Chrome 无头截屏，中文字一个不差。
- **文风四规则**：短句一句一事、主谓相邻、不堆名词、不自造比喻——写在 `references/style-rules.md`，标题同样适用。
- **图注以实际截图为准**：说明文件和图像识别都可能是错的，引用数字前必须亲眼看过原图（教训写成流程）。
- **截图重拍安全**：源目录是唯一真相，hash 链路让任何一张图被换掉都会被门禁拦下。

## 仓库结构

```
SKILL.md           技能主文档（含 8 句开场白）
scripts/           全部脚本与模板（可移植：相对路径，在项目根目录运行）
references/        文风规则 / 素材清单 schema
```

## License

MIT
