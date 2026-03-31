# CLAUDE.md — my-docs 项目规则

## 项目简介

Howard 的个人技术学习笔记库，自动发布至 GitHub Pages。
线上地址：https://howard-agent.github.io/my-docs/

---

## 工作规则

### Session 结束前必须执行
每次 session 结束前，自动将本次工作内容追加到本文件底部的「工作日志」部分，格式如下：
- 日期（YYYY-MM-DD）
- 完成的主要工作
- 重要决策及原因
- 数据分析结论（如有）

重要决策和数据分析结论必须记录，不可省略。

### 自动化流程
- 处理文档统一使用 `scripts/process_doc.py`
- 所有新文档通过 `inbox/` 投递，禁止直接在根目录放 .md 文件
- 每次生成 HTML 后必须 git commit + push，并验证推送成功

### 隐私脱敏规则
IP、姓名、密码、Token、邮箱、电话、序列号等敏感信息必须替换为占位符，详见 `scripts/process_doc.py` 中的 prompt。

---

## 工作日志

### 2026-03-31

**主要工作：**
- 设计并实现 inbox/ 自动化 MD→HTML 发布流水线
- 修复多个 bug 并完善去重、推送验证机制

**重要决策：**
- 使用 `claude -p` CLI 而非 Anthropic SDK，复用 Claude Code 已有 quota，无需额外 API key
- Claude 输出格式改为「元数据 JSON + `===HTML_START===` + HTML 正文」分离结构，解决 HTML 内特殊字符导致 JSON 解析失败的问题
- 使用 MD5 内容 hash 去重（跨 session 持久），而非仅依赖文件名，防止同内容改名重复处理
- git push 后增加 `git status -sb` 验证步骤，防止推送静默失败
- watcher 自动修正 Mac 拖入文件时产生的 `.md.md` 双扩展名

**基础设施：**
- `~/.tmux.conf` 开启鼠标模式，支持滚轮和手机触屏滑动
- tmux session 改名为 `work`，手机 SSH 后 `tmux attach -t work` 接回
- watcher 守护进程写入 `~/.bashrc`，WSL 启动自动运行
