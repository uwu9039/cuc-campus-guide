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
git commit -m "v0.6 校园办事向导"
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
- 个人数据查询（校园卡、课表）依赖本地浏览器扩展，创空间上的公开站点不提供登录入口，也不接收个人数据。
- 创空间仓库和 GitHub 是两套仓库，互不影响；改完数据要重新跑一次 `build_modelscope.py` 再推。
