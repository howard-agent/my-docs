这是一份为您整理的 NotebookLM 登录与网络环境排查记录总结。您可以直接复制以下 Markdown 内容并保存为 `.md` 文件留作备忘。

---

# NotebookLM 无法登录与区域限制排查记录

## 📌 问题背景

- **设备环境**：MacBook Pro (后续涉及 Windows + WSL 辅助环境)
    
- **代理工具**：v2rayN
    
- **故障现象**：通过 Chrome 映射的 NotebookLM Web App 突然注销，重新打开后**没有登录按钮**，页面卡在产品介绍页（URL 尾部强制带有 `?location=unsupported` 参数）。手机端同步测试时提示 `Could not load NotebookLM`。
    

---

## 🔍 核心原因分析

经过多轮排查，导致 NotebookLM 判定为“不支持地区”的原因主要有三个层级：

1. **节点出口 IP 不合规**：初期使用了“广港 IEPL”节点，出口 IP 落在香港，而 NotebookLM 目前不支持香港地区。
    
2. **WebRTC 真实 IP 泄露（最隐蔽的原因）**：即使代理 IP 切换到了美国，桌面浏览器依然通过底层 WebRTC 协议向 Google 暴露了真实的中国局域网/公网 IP（`120.229.x.x` 和带有中国国旗的标识），导致伪装失效。
    
3. **DNS 污染与缓存死锁**：URL 携带的 `location=unsupported` 会被浏览器缓存，且部分 DNS 解析未走代理通道（如直连了 `223.5.5.5`），导致后续验证依然失败。
    

---

## 🛠️ 最终解决方案与操作步骤

### 第一步：更换合规的节点 IP

- **操作**：放弃使用香港或特征明显的国内中转节点。
    
- **要求**：切换至**美国 (US)**、**新加坡 (SG)** 或 **日本 (JP)** 等原生支持地区的节点。
    

### 第二步：彻底封堵 WebRTC 泄露（关键步骤！）

在不开启全局 TUN 模式的情况下，必须从浏览器层面阻止真实 IP 告密。

1. 在 Chrome 应用商店安装 **WebRTC Leak Prevent** 插件。
    
2. **核心设置**：进入插件选项，将 `WebRTC IP handling policy` 设置为 **`Disable non-proxied UDP (force proxy)`**。（_注：默认选项无法完全隐藏公网 IP_）。
    
3. **验证方法**：访问 [BrowserLeaks WebRTC Test](https://browserleaks.com/webrtc)，确保 **Public IP Address** 一栏显示为空白 (`-`) 或仅显示代理服务器的美国 IP。
    

### 第三步：清除浏览器“错误记忆”

1. 彻底关闭所有 Chrome 窗口（包含无痕模式）以及映射生成的本地 Web App 窗口。
    
2. 按 `Command + Shift + Delete` 清除近期的 Cookie 和缓存。
    
3. **重新访问**：在浏览器地址栏**手动输入纯净网址** `https://notebooklm.google.com/`，切勿直接刷新带有 `unsupported` 尾缀的历史页面。
    
4. 成功看到 “Try NotebookLM” 并登录后，可重新生成桌面 Web App（PWA）。
    

---

## ⚠️ 附加避坑指南：关于 TUN 模式与 DNS 死锁

在尝试解决网络问题时，曾尝试开启 v2rayN 的 **TUN 模式**，但引发了大量 `i/o timeout` 报错（如无法连接阿里 DNS `223.5.5.5:443`）。

- **原因**：TUN 模式强制接管所有网卡流量，导致代理工具在尝试通过直连网络去解析节点域名或国内 DNS 时，流量又被绕回了 TUN 虚拟网卡，形成了**路由环路（Routing Loop）**和 DNS 解析死锁。
    
- **结论**：如果**系统代理 + WebRTC 插件**已经能让网页版顺畅运行，**不建议强制开启 TUN 模式**，以避免复杂的底层网络冲突。
    

## 💻 Windows 环境补充建议 (针对 WSL 用户)

在 Windows 环境下如果一切正常，但 WebRTC 仍有暴露：

- **现状分析**：由于已经建立 Session，Google 暂未阻断连接，但这是一个“定时炸弹”，未来如果触发深度检测可能再次掉线。
    
- **处理建议**：同样在 Windows 的桌面浏览器中安装并严格配置 WebRTC 防泄露插件。WSL 内部的命令行操作不受浏览器 WebRTC 影响，无需特殊处理。
    

---

**这份文档是否涵盖了我们需要记录的所有重点？如果你需要在 Windows 环境下长期稳定使用，需要我为你提供一份 v2rayN 自定义路由规则的配置代码（让 Google 域名强制走代理）吗？**