# Howard's Learning Docs

个人技术学习笔记库，自动发布至 GitHub Pages。

🔗 **https://howard-agent.github.io/my-docs/**

---

## 文档

| 文档 | 标签 |
|------|------|
| [Claude Code Session 管理与多设备工作流](https://howard-agent.github.io/my-docs/claude-code-session-management.html) | Tools · Workflow |
| [基础网络环境搭建](https://howard-agent.github.io/my-docs/fundamental-network-setup.html) | DevOps · Tools |
| [向日葵智能插座 C1 Pro · 远程开机排障实录](https://howard-agent.github.io/my-docs/sunflower-remote-boot-guide.html) | Tools · DevOps |
| [NotebookLM 无法登录与区域限制排查记录](https://howard-agent.github.io/my-docs/notebooklm-login-troubleshooting.html) | Network · Tools |
| [OpenClaw 3.8 多 Agent 架构与网络配置实战记录](https://howard-agent.github.io/my-docs/openclaw-multi-agent-network-config.html) | AI · Network · Workflow |

---

## 自动发布流程

把 `.md` 文件拖入 `inbox/` 文件夹，剩下的自动完成：

```
inbox/新文档.md
    ↓ watcher 检测（每 4 秒轮询）
    ↓ claude -p 脱敏 + 转 HTML
    ↓ 更新 index.html
    ↓ git commit + push
GitHub Pages 自动部署（约 30 秒）
```

**隐私脱敏**：IP 地址、姓名、密码、邮箱、电话、Token 等自动替换为占位符。

### 启动监控

```bash
./scripts/start_watcher.sh        # 前台运行
./scripts/start_watcher.sh -d     # 后台守护进程
./scripts/stop_watcher.sh         # 停止
tail -f inbox/watcher.log         # 查看实时日志
```

WSL 启动时自动运行（已写入 `~/.bashrc`）。

### 注意事项

- 从 Mac 拖入文件时确保放入 `inbox/` 目录，而非项目根目录
- 同内容文件会自动跳过（基于 MD5 去重）
- 处理成功的文件移至 `inbox/processed/`，失败的移至 `inbox/failed/`
