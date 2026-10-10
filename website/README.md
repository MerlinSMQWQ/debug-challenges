# 公开赛题内容同步与发布

网站 https://debug.yuroteam.cn/ 已有浏览器读取 GitHub 的机制。推荐继续把 **`main` 作为公开内容发布分支**：每次访问／刷新网站，从仓库读目录与题目。Mac 不需要常驻，也不需要服务器拉取仓库、Webhook、定时任务、SSH Actions 密钥或新系统服务。助手云端只需已有 Git、Python 和 GitHub 连接，就能编辑、备份、提交候选题，并由 Actions 验证容器。

制作验证与备份的统一约定在根 [AGENTS.md](../AGENTS.md)。本目录是现有云服务器网站的前端覆盖补丁，不是新网站、全站源码或生产自动部署配置。

## 已检查的当前机制

2026-10-10 只读下载线上 `app.js`，SHA-256 为 `c4774b1524b6f34b400ef194639a68ec8973b91b40454515802bb146c87e34d1`，与本机迁移源码完全相同。当时 GitHub `main` 为 `25c1b24b31dd6c7c99bbafe7e7c80a148039a644`，本机原仓库另有 `35c9fda`、`f679bba` 两项未推送提交，工作区干净。

旧前端每次打开从 `main/README.md` 读五列目录，按日期读公开 Markdown；提交接口也依据 README 检查已发布日期。旧手册使用部署时副本，备用快照固定在旧版本，读取过程可能混入两次 push 的内容。

这次保留五列目录以兼容已经在线的前端：新正式题 #001 与测试题 #000 都能被旧前端识别。日期 `2026-10-09` 仍是旧题数据身份，链接 `#/challenge/2026-10-09` 不变；只调整展示编号与题目名称，不改写旧题历史记录、数据库、榜单归属或评分。

## 补丁做什么

- `public/app.js`、`public/content-source.mjs`：先查 `main` 的提交 SHA，再按同一 SHA 读取目录、题目和手册；公开文档使用路径白名单。连接失败时明确标注使用备用材料及日期，手册也显示备用提示。
- `tools/build_public_content.py`：只从根 README、手册、题目入口和入口引用的公开 Markdown 生成 `snapshot.json`、`handbook.md`，不遍历 organizer、账户、提交、成绩、数据库或配置。拒绝私有链接、符号链接、重复目录身份和不合理目录格式。
- `Validate public content` Actions：在 `main`、`draft/**` 的相关 push 和相关 PR 做只读验证、生成公开 artifact。**无 SSH、服务器写入、数据库迁移或自动部署步骤。**
- `Official 001 container` Actions：复用既有 Docker/Compose CI 模式，对候选提交验证本题标准现场。制作任务的容器验收以这一提交的结果为依据。

公开内容触发路径为 `README.md`、`Debug 挑战赛手册.md`、`challenges/**`，以及本目录、生成器和其测试／工作流。`参考文档.md` 是仓库选题参考，不是网站题目正文。前端、登录、后端 API、依赖、服务配置的变更仍属于网站部署；它们不会随普通题目 push 自动安装。

## 本地轻量检查

先备份，再编辑；不运行本地 Docker。

```sh
python3 tools/backup_project.py --destination ../debug-backups
python3 -m unittest discover -s tools -p 'test_public_content.py' -v
node --test website/tests/content-sync.test.mjs
node --check website/public/app.js
python3 tools/build_public_content.py --output dist/public-content --ref main
```

`--ref main` 只用于未发布草稿预览。发布包必须使用已经提交的完整 SHA；Actions 使用 `github.sha`，不会写回仓库。输出目录限制为四个公开文件：`app.js`、`content-source.mjs`、`snapshot.json`、`handbook.md`。

本次 Python 公开边界检查 6 项通过，Node 内容读取检查 6 项通过；轻量事故检查 2 项通过，隔离参考修复验收 7 项通过。浏览器草稿验收使用本地公开 fixture，验证目录、正式首题、原日期链接和手册导航；没有登录、提交、复制评分材料或评分。本文初次撰写时标准容器对应 Actions **尚未验证**；后续必须查看候选提交确切 SHA 的运行结果，不能用旧 main CI 或历史本地 Docker 记录替代。

## 生产影响与需要的授权

1. **推送候选范围。** 先审阅本次提交和它的父提交，再明确授权推送候选分支。候选分支 `draft/official-001-ci` 从 `25c1b24` 建立，仅提交本次 33 个文件的准确范围；选题参考目录内容单独纳入，未继承 `35c9fda`、`f679bba` 两项积压提交。旧题运行配置和操作材料保持远端基线，原 checkout 的用户映射修复仍保留在原本地提交中。推送 `draft/**` 只跑验证，不改变网站读取的 main。
2. **取对应 Actions 结果。** 检查 `Official 001 container` 与 `Validate public content` 都属于待发布的确切 SHA；若 CI 失败，修复后重新验证新 SHA。新题未通过这一关时保持待发布。
3. **发布到 main。** 用户授权把审核且验证通过的范围发布到 main 后，网站访问／刷新时可读到新题；现有前端已支持五列目录，因此这一步本身不依赖前端补丁上线。GitHub 或访问者网络可能导致延迟／失败，页面会显示备用状态。已打开页面需刷新，不主动打断填写中的表单。
4. **一次性上线四个前端文件。** 要获得固定 SHA 读取、手册同步和新的备用材料，需要另外授权部署本补丁。使用获批 main SHA 的 Actions artifact；先备份服务器现有四个公开文件及应用版本，核对压缩包可读和哈希，不导出数据库或机密配置。只更新现有应用 `public/` 内这四个文件；新静态路径需要受控重启既有 `debug-challenges.service`，可能造成短暂访问中断。Next.js 生产服务启动时枚举 public 文件，不能假定新增模块无需重启就会被识别。
5. **验收与回退。** 检查首页正式 #001、测试 #000、两个日期链接、手册、断网备用提示和原登录入口。只读查看已有成绩；不运行会创建测试账户或答卷的生产 smoke 测试。失败时恢复备份的公开文件并重启原服务。不得覆盖 `.env`、`data/`、SQLite、APP_ORIGIN、登录配置或 Cloudflare 隧道；无数据库迁移，不改接评分队列。

后续普通题目与手册更新 push 到 main，即可沿已上线机制读取；备用 artifact 自动生成，但服务器上的备用文件不会被自动替换。需要更新离线备用包时，另行授权应用该 SHA 的公开 artifact。自动替换服务器备用包或全站自动部署是后续范围，不能把本次 CI 构建称为生产自动部署。

本题新答案保存在被 Git 忽略的 `organizer/2026-10-10/`，并另有私有备份，不在公开 artifact。现有“复制评分材料”和服务器评分实现仍从 GitHub 读答案，新题赛前不会公开该来源，因此新题赛后材料需由出题者单独提供；未来要在线评分，应另行决定私有参考资料的接入方式，不能为了让按钮工作而公开答案。

## 备份恢复

`backup_project.py` 保存源码、未跟踪源码、被忽略的必要 organizer 材料和 Git bundle，逐文件校验归档哈希，并验证 bundle。输出在仓库之外，不能提交或当成公开 artifact。它排除数据库、环境文件、密钥、凭证、依赖及运行／构建产物；其他重要非源码文件应在修改前单独备份。备份无自动清理。

恢复时在新的私有目录读取 `manifest.json`，先 `git bundle verify`，再从 bundle 创建独立 checkout，把 `project-source.tar.gz` 解到隔离目录，逐文件比对 manifest。不要直接覆盖当前生产目录或正在进行的比赛数据。

本次原基线备份是修改开始后从未改动的 `f679bba` 重建，已与 39 个 Git 文件逐字节比对；不是事前归档。另保存当前未提交／未跟踪材料 checkpoint，并从引入备份要求后在后续更新批次前运行备份。路径与校验记录在本次任务私有 `backups/`，不进入仓库。
