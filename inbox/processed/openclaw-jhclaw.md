# OpenClaw 3.8 多 Agent 架构与网络配置实战记录 (jhclaw)

**文档状态**: 基础环境已跑通，准备进入具体业务（亚马逊运营）Agent 编排阶段。
**部署环境**: 飞牛OS (FNOS) NAS / Docker 容器环境
**软件版本**: OpenClaw 2026.3.8

---

## 1. 核心大模型通道 (Providers) 接入指南

在 OpenClaw 3.8 中，配置 Provider 的校验机制极其严格（强迫症级别），不同类型的平台接入方式有所不同。

### 1.1 AIHubMix (官方插件自动化接入)
AIHubMix 提供了专用的认证插件，可以自动同步分类所有模型（涵盖 Claude、Gemini、OpenAI 等），是最省心的接入方式。
* **安装插件**: `openclaw plugins install @akaknele/aihubmix-auth`
* **重启容器**: 退出容器，宿主机执行 `sudo docker restart openclaw`
* **交互式认证**: 
    ```bash
    openclaw models auth login --provider aihubmix --method api-key --set-default
    ```
    *(按提示输入 API Key，插件会自动配置路由和 Header)*

### 1.2 OpenRouter (系统原生免驱接入)
OpenRouter 在 3.8 版本中作为原生 Built-in 支持，**不需要使用上述的 plugin login 命令**。
* **配置方式**: 可以直接通过修改配置表或使用 `openclaw config set auth.openrouter "<Your_OpenRouter_Key>"` 来激活。调用时直接在模型前加前缀即可（如 `openrouter/anthropic/claude-3-opus`）。

### 1.3 VectorEngine (极其严格的 CLI 写入踩坑记录)
VectorEngine 作为 OpenAI 兼容接口，在尝试使用 `openclaw config set` 逐行写入时，遭遇了 OpenClaw 严格的**实时完整性校验**拦截（缺少 baseUrl、缺少 models 数组等都会直接报错阻断）。
* **最终解决方案 (复合 JSON 注入)**:
    必须将完整的对象（包含 api类型、URL、Key 以及 Models 数组）一次性写入：
    ```bash
    openclaw config set models.providers.vectorengine '{ "api": "openai-completions", "baseUrl": "[https://api.vectorengine.ai/v1](https://api.vectorengine.ai/v1)", "apiKey": "sk-xxxxxx", "models": [ { "id": "deepseek-v3", "name": "DeepSeek V3" }, { "id": "minimax-abab6.5-chat", "name": "MiniMax" } ] }'
    ```

---

## 2. 智能体 (Agent) 的配置与指派

当 Provider (管道) 接通后，需要创建具体的 Agent (角色) 并指派对应的 Provider 和 Model。
* **基础命令规范**:
    ```bash
    openclaw config set agents.<角色名>.provider "<对应Provider名称>"
    openclaw config set agents.<角色名>.model "<对应模型ID>"
    ```
* **实战举例 (配置 worker)**:
    ```bash
    openclaw config set agents.worker.provider "vectorengine"
    openclaw config set agents.worker.model "deepseek-v3"
    ```
*(配置完成后，重启容器，在飞书内通过 `/worker <指令>` 即可调用该分身)*

---

## 3. 网络与外网 Web UI 访问排查手册

我们在尝试访问 `http://<IP>:18789/?token=...` 的 Web GUI 时遇到了各种网络阻击，以下是排查经验：

### 3.1 宽带与 DDNS 限制
* **现象**: 使用腾讯云 DDNS 域名访问报 `ERR_CONNECTION_CLOSED`。
* **原因**: 家宽无公网 IPv4，仅配置了 IPv6 DDNS。当外网设备（如手机移动网络或部分公司 Wi-Fi）不支持 IPv6 时，域名解析直接失效。

### 3.2 Tailscale + v2rayN 冲突处理
为了实现“随处访问”，启用了 NAS 上的 Tailscale 内网穿透。
* **冲突点**: Mac 端的 v2rayN 代理规则会劫持/丢弃 Tailscale 的虚拟局域网流量。
* **解决方案**: 必须在 v2rayN 中开启 **Enable Tun (虚拟网卡模式)**，让系统级路由正确接管科学上网和 Tailscale 的 100.x.x.x 流量。

### 3.3 终极 503 报错 (HTTP ERROR 503)
网络打通后，通过 Tailscale IP 访问依然报 503。
* **原因 1**: 容器内的 OpenClaw Gateway 默认只监听了 `127.0.0.1`，拒绝了外部（包括 Tailscale 虚拟网卡）的访问。需要在 Docker 环境变量中补充 `HOST=0.0.0.0`。
* **原因 2**: 频繁修改配置导致 Gateway 进程假死。可通过 `openclaw gateway stop` / `start` 尝试重启进程。
*(由于 Web UI 持续 503，后续果断转向纯 CLI 命令行完成配置。)*

---

## 4. 下一阶段：亚马逊多 Agent 运营矩阵规划

目前底层接口已全数打通，下一步将结合飞书群组，构建专属的亚马逊 AI 运营团队。

### 架构草案 (基于系统目录结构)

| Agent 目录 / 角色 | 拟定身份 (Personality) | 推荐调用模型 | 核心预设技能 (Skills) |
| :--- | :--- | :--- | :--- |
| **a0-amazon-brain** | 决策中枢 / CEO | Claude 3 Opus (OpenRouter) | 跨部门调度、SOP 审核、最终决策 |
| **a1-amazon-listing** | 视觉文案 / SEO | Claude 3.5 Sonnet (AIHubMix)| 编写高质量 Listing、埋词、文案优化 |
| **a2-amazon-ads** | PPC 投放投手 | Gemini 3.1 Pro (AIHubMix) | 报表分析、ACOS 优化、竞价建议 |
| **a3-amazon-inventory**| 供应链及库存主管 | DeepSeek V3 (VectorEngine)| 监控发货进度、测算补货周期 |
| **a4-amazon-finance** | 财务与核算 | DeepSeek V3 (VectorEngine)| 利润率核算、头程尾程成本计算 |
| **a5-amazon-xuanpin** | 选品及市场调研 | Gemini 3.1 Pro (AIHubMix) | 联网搜索竞品、市场容量评估 |
| **a6-amazon-logistics**| 物流跟踪专员 | DeepSeek V3 (VectorEngine)| FBA 货件状态追踪、异常预警 |

### 待办事项 (Next Steps)
1.  **系统提示词 (System.md)**: 为每个 Agent 编写独有的 System Prompt，设定红线与工作标准。
2.  **知识库挂载 (RAG)**: 将各个岗位的业务手册通过 VectorEngine 的 Text-Embedding 向量化，喂给对应的 Agent。
3.  **飞书群协作逻辑**: 让不同 Agent 在同一个群聊中相互 `@` 对话，形成业务流水线自动流转。