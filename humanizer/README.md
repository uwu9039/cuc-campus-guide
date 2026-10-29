# humanizer-zh · 本项目用法与引用

## 它是什么

`humanizer-zh` 是一套**中文文本润色规则**：把空话、重复、模板化表达改掉，让文字更自然，
同时**保留事实、数字、确定程度和作者声音**。它不是 AI 检测器，也不判断作者身份。

本项目的所有面向用户的文字（页面提示、按钮、反问话术、错误提示）都按这套规则过了一遍。

## 引用与来源

本目录的 `RULES-zh.md` 是**依据以下来源整理的检查清单**，不是原文转载：

- [blader/humanizer v3.0.0](https://github.com/blader/humanizer/blob/v3.0.0/SKILL.md) —— A–E 分类、声音校准
- [Humanizer-zh PR 39](https://github.com/op7418/Humanizer-zh/pull/39) —— 中文分类与 F 组检查点
- [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) —— 简洁表达
- [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) —— 观察来源，不作检测依据

使用方式：作为编辑准则参考，不复制其代码或全文。若原项目有 license 要求，以其仓库声明为准。

## 在本项目里的边界（硬约束）

改写**只动措辞**，以下一律不动：

| 不动的东西 | 例子 |
|---|---|
| 数字 | 1500 元、14:00-16:30、5 个工作日、16 位验证码 |
| 部门名 | 本科生院、学生工作部（处）、后勤保障处 |
| 办理方法 | 先找辅导员签字、到艺术与传播大楼三层 |
| 文件名与文号 | 中传教字〔2021〕209 号、p.106 |
| 原文引文 | 证据层引文一个字都不改 |

改的只是：铺垫、重复、拔高、客服腔、生硬连接词。

## 怎么检查

```bash
.venv\Scripts\python.exe tools/humanize_lint.py
```

扫描 `index.html` 与 `app.py` 里的用户可见文案，报出疑似 AI 腔的句子。
只报告，不自动改——改文案要人看上下文。
