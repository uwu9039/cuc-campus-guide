# 魔搭创空间部署

创空间选 **Docker** 类型、免费 CPU 实例即可。平台把 **7860** 端口作为对外入口，`Dockerfile` 已按这个端口写好。

## 1. 建空间

modelscope.cn → 创空间 → 新建：

- 部署框架：Docker
- 可见性：公开
- 硬件：免费 CPU（2 核 16G）
- 新仓库默认分支是 `master`

## 2. 组装上传目录

在本机仓库根目录执行：

```bat
.venv\Scripts\python.exe tools\build_modelscope.py
```

产物在 `_modelscope_bundle/`，约 80 MB（不带向量索引则约 8 MB）。目录里只有运行时文件，凭证、个人数据扩展包、隔离语料都不会被带进去。

向量索引 `vectors.npy` 约 60 MB，个别情况下会被平台的大文件校验拦下。真遇到就改用：

```bat
.venv\Scripts\python.exe tools\build_modelscope.py --no-vector
```

不带向量索引时问答照常，只是规则没命中时少一层原文线索，`/api/search` 会返回 503。

## 3. 推到创空间

```bash
git clone https://www.modelscope.cn/studios/<用户名>/<空间名>.git
# 把 _modelscope_bundle/ 里的全部内容复制到克隆目录根部（Dockerfile 和 README.md 要在根目录）
cd <空间名>
git add -A
git commit -m "v0.8 校园办事向导"
git push origin master
```

令牌在 modelscope.cn 的「访问令牌」页生成，推送时当密码用。

## 4. 可选：模型核对

创空间设置里加环境变量 `DEEPSEEK_API_KEY`，拍照核对与模型裁决才可用；不填也能问答。

## 5. 部署后核验

```bash
curl https://www.modelscope.cn/studios/<用户名>/<空间名>/api/health
```

健康检查里应看到条目数 8573、预置问法 764。再打开页面问一句「校园卡丢了怎么办」，回答里应带引文与来源。

## 注意

- 不要上传 `.env`、`download.devtools`、`aia-api.json`、`web-next/campus-guide-personal-data.zip`；`build_modelscope.py` 已经把它们排除在外。
- 三个界面（`/field`、`/desk`、`/classic`）都在包里，共用同一个后端与同一份数据。打开站点根路径会自动跳到 `/field`（302，带 `?q=` 也照跳）。手机端与微信内嵌浏览器可直接用 `/field`。
- 个人数据（校园卡余额、课表）在公开站点上只给两个官方网址入口，页面本身不读取、不接收、不转发任何个人数据；实时查询要学生本人在官方系统登录完成。
- 创空间仓库和 GitHub 是两套仓库，互不影响；改完数据要重新跑一次 `build_modelscope.py` 再推。

## 出包前提（v1.0.1 起）

	ools/build_modelscope.py 现在会把**章节索引**（sections_index.py + _review_items/sections/，531 份 JSON）
一起打进包。缺这份目录时脚本会直接 SystemExit，**不再静默降级**——因为不带它，云端 ② 会静默关闭
（sections_index.stats() 返回 {}），页面上看不出任何异常。

所以出包必须在**带 _review_items/sections/ 的工作机**上跑：

`ash
python tools/build_modelscope.py --out _modelscope_bundle_full
`

.gitignore 忽略了 _review_items/，裸 clone 上跑不了出包——这是有意的。
