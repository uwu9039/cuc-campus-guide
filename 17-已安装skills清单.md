# 17 · 已安装 skills 清单（全局）

> 2026-10-27 安装 · 6 个 skill + 1 个 CLI，全部**用户级全局**，不绑定本工程。
> 目录写在 `（本地路径已隐藏） 之外，换项目照样能用。

## 一、装在哪

| 位置 | 内容 | 作用范围 |
|---|---|---|
| `（本地路径已隐藏） | humanizer-zh · stop-slop · evaluation · advanced-evaluation · tool-design · skill-seekers | **DSH 所有项目**（会话启动自动注入目录，无需在工程里放副本） |
| `（本地路径已隐藏） | 同 6 个（镜像） | Codex CLI 全局 |
| `（本地路径已隐藏） | skill-seekers 3.0.0 独立虚拟环境（含 `[mcp]` 额外依赖） | 不与工程 `.venv` 混装，`requirements.txt` 不受污染 |
| `（本地路径已隐藏） / `.cmd` | PATH 垫片 | 任何 shell 里直接敲 `skill-seekers` |

`skill-seekers` 的 bin 目录同时写进了 **用户级 PATH**（`[Environment]::SetEnvironmentVariable('Path',...,'User')`），
所以新开的任何终端、任何项目都能调；`.dsh\bin` 垫片让**当前会话不用重启**也能用。

## 二、六个 skill 各自管什么

| skill | 来源 | 用途 |
|---|---|---|
| `humanizer-zh` | [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) | 中文去模板腔：31 个检查点，A–F 六类；保留事实与确定程度 |
| `stop-slop` | [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) | 英文 AI 腔清除 + 五维打分（直给/节奏/尊重读者/像人/密度） |
| `evaluation` | [Agent-Skills-for-Context-Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering) | 确定性检查、回归套件、多维 rubric、质量门 |
| `advanced-evaluation` | 同上 | LLM-as-judge：直接打分、两两比较、判官偏差与校准 |
| `tool-design` | 同上 | 工具契约、描述可路由、错误可执行、工具集收敛 |
| `skill-seekers`（skill 名 `skill-builder`） | [yusufkaraaslan/Skill_Seekers](https://github.com/yusufkaraaslan/Skill_Seekers) | 把文档站 / 仓库 / PDF / 视频转成 skill |

## 三、skill-seekers 怎么用（CLI 才是能跑的那半）

它自带的 skill 是**MCP server 的说明书**（40 个工具），本机 DSH 没有 MCP 注册入口，
所以那条路暂时是空的；**CLI 已经装好，能直接用**：

```bash
skill-seekers --version                 # 3.0.0
skill-seekers scrape <文档站URL>        # 抓文档站
skill-seekers pdf <本地PDF>             # 从 PDF 抽
skill-seekers github <owner/repo>       # 抓仓库
skill-seekers analyze <本地目录>        # 分析代码库
skill-seekers package <skill目录>       # 打包成目标平台格式
```

MCP 通道（要用时）：`python -m skill_seekers.mcp.server_fastmcp`，需宿主支持 MCP 注册。

対本工程的用法：619 份语料里挑一个专题（如学籍流转），用 `skill-seekers scrape` / `pdf`
压成一个独立 skill，比继续往 `items.json` 里堆条目更可移植。

## 四、环境边界（这轮踩到的，别再重试）

| 目标 | 结果 |
|---|---|
| `github.com` / `raw.githubusercontent.com` / `cdn.jsdelivr.net` | **SSL 握手超时**，python、curl、node 全不通 |
| `api.github.com` | 通（限速 60 次/小时，未认证） |
| 仓库 tarball 下载（`codeload.github.com`） | 不通，600 秒超时 |
| 可行路径 | **contents API 逐文件 base64**：`GET /repos/{owner}/{repo}/contents/{path}?ref=HEAD` |

所以以后装外部 skill 只有两条路：`api.github.com` 逐文件拉（脚本 `tools/_install_skills.py`），
或在本机能用 `web_fetch` 的场合抓单个 `SKILL.md`。

## 五、卸载 / 回滚

```powershell
Remove-Item -Recurse "$env:USERPROFILE\.dsh\skills\<name>"
Remove-Item -Recurse "$env:USERPROFILE\.codex\skills\<name>"
# 只卸 CLI：
Remove-Item -Recurse "$env:USERPROFILE\.dsh\runtimes\seeker-venv"
# 并从用户 PATH 里删掉 ...\seeker-venv\Scripts
```

skill 是可逆的纯文本目录，删掉即失效，不会留下注册表或服务。
