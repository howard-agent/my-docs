# Session Summary — my-docs 自动化发布系统搭建

**日期：** 2026-04-02  
**项目：** https://howard-agent.github.io/my-docs/

---

## 已完成功能

### 1. inbox/ 自动化 MD→HTML 发布流水线

**文件：**
- `scripts/process_doc.py` — 核心处理器：脱敏 + 转 HTML + 更新 index + git push
- `scripts/watcher.py` — 轮询守护进程（每 4 秒），检测 inbox/ 新文件
- `scripts/start_watcher.sh` — 启动脚本（前台 / `-d` 后台模式）
- `scripts/stop_watcher.sh` — 停止守护进程
- `inbox/` — 文件投递目录；`processed/`、`failed/` 自动归档

**流程：**
```
拖入 inbox/xxx.md
  → watcher 检测
  → claude -p 脱敏 + 转 HTML（复用 Claude Code quota）
  → 写出 xxx.html
  → 更新 index.html（插入首位，最新在上）
  → git commit + push --porcelain
  → 验证推送成功（git status -sb 检查不领先 origin）
  → 原文件移入 inbox/processed/
```

### 2. 隐私脱敏

Claude 自动将以下内容替换为占位符：  
IP → `[内网IP]` / `[公网IP]`、姓名 → `[姓名]`、密码/Token → `[密钥]`、邮箱 → `[邮箱]`、电话 → `[电话]`、域名 → `[域名]`、序列号 → `[序列号]`

### 3. session-archiver Agent 集成（追加模式）

- **命名规则：** `topic_YYYYMMDD.md`（如 `tailscale_network_20260401.md`）
- **行为：** 若 `tailscale-network.html` 已存在 → 追加新日期章节；否则新建
- **效果：** 同一话题只有一个 HTML，内容按日期累积，index 卡片日期自动更新并移到首位

### 4. 去重保护（三层）

| 层 | 机制 |
|---|---|
| watcher 内存 | `seen` 集合，同 session 内跳过 |
| watcher 持久 | 读取 `processed/` + `failed/` 的 MD5 hash，跨 session 去重 |
| process_doc | HTML 文件已存在则拒绝覆盖 |

### 5. Mac 拖入兼容

自动修正 `.md.md` 双扩展名（VSCode Remote + Mac 拖入时产生）

### 6. tmux 远程工作流

- `~/.tmux.conf`：`set -g mouse on`，支持滚轮 + 手机触屏
- Session 名：`work`，手机 SSH 后 `tmux attach -t work`
- watcher 写入 `~/.bashrc`，WSL 启动自动运行

### 7. 密码保护（单文件）

`q2-2026-inventory-clearance-plan.html` 添加客户端 MD5 密码验证  
密码存为 hash，同 session 只需输入一次（sessionStorage）

### 8. 项目基础设施

- `CLAUDE.md` — 工作规则 + session 日志（自动追加）
- `README.md` — 项目介绍 + 使用说明
- `.gitignore` — 排除 `inbox/processed/`、`inbox/failed/`、`__pycache__` 等

---

## 关键决策

| 决策 | 原因 |
|---|---|
| 用 `claude -p` 而非 Anthropic SDK | 复用 Claude Code 已有 quota，无需单独 API key |
| 元数据 JSON + `===HTML_START===` + HTML 分离格式 | HTML 内特殊字符会破坏 JSON 解析 |
| MD5 内容 hash 去重 | 同内容改名重复投递问题 |
| `git push --porcelain` + 推送后验证 | push 静默成功但实际未推的 bug |
| `topic_YYYYMMDD.md` 追加模式 | 避免 session-archiver 每日归档产生大量 HTML |
| 新文档插到 index 首位 | 用户习惯：最新内容在最前 |
| 客户端 MD5 密码保护 | GitHub Pages 无服务端，适合轻量访问控制 |

---

## 待办事项

- [ ] 测试 session-archiver 追加模式的完整流程（等第一次真实归档触发）
- [ ] 考虑为 index.html 添加标签筛选功能
- [ ] 密码保护目前是纯前端，如需更强保护考虑 Cloudflare Access

---

## 重要数据

- GitHub Pages 推送后约 30 秒生效
- watcher 轮询间隔：4 秒
- Claude 处理单文件耗时：约 60~120 秒（含脱敏 + HTML 生成）
- claude -p 调用超时设置：300 秒
