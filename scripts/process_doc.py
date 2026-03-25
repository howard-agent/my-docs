#!/usr/bin/env python3
"""
处理单个 MD 文件：隐私脱敏 → 转 HTML → 更新 index.html
用法: python3 process_doc.py <文件路径.md>
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).parent.parent
INDEX_HTML = BASE_DIR / "index.html"

# 可用的 tag 类型（与 index.html CSS 对应）
TAG_CLASS = {
    "Tools":    "tools",
    "Workflow": "workflow",
    "AI":       "ai",
    "DevOps":   "dev",
    "Network":  "dev",
    "Dev":      "dev",
    "Security": "dev",
}

# ── 读取现有 HTML 模板的 CSS ──────────────────────────────────────────────────

def read_template_css() -> str:
    """从已有文档中提取 CSS，用于告知 Claude 目标风格。"""
    template = BASE_DIR / "sunflower-remote-boot-guide.html"
    if not template.exists():
        return ""
    content = template.read_text(encoding="utf-8")
    start = content.find("<style>")
    end = content.find("</style>") + len("</style>")
    return content[start:end] if start != -1 else ""


# ── 构建 Prompt ───────────────────────────────────────────────────────────────

def build_prompt(md_content: str, today: str, css: str) -> str:
    return f"""你是技术文档处理助手。请对下方 Markdown 完成两项任务。

===任务 1：隐私脱敏===

将以下类型的个人隐私信息替换为占位符（技术命令和软件名无需脱敏）：
- 真实姓名 → [姓名]
- 内网 IP（192.168.x.x / 10.x.x.x 等）→ [内网IP]
- 公网 IP → [公网IP]
- MAC 地址 → [MAC地址]
- 密码、Token、API Key、密钥 → [密钥]
- 电子邮箱 → [邮箱]
- 手机/电话 → [电话]
- 真实生产域名 → [域名]
- 设备序列号/SN → [序列号]
- 真实地址 → [地址]
- 微信/QQ/账号 ID → [账号ID]

===任务 2：转换为 HTML===

将脱敏后内容转换为完整 HTML 文档，CSS 风格必须与以下参考完全一致：
{css}

HTML 必须包含：
1. 返回首页：<a class="back-link" href="index.html">← 返回目录</a>
2. header：含 emoji 图标、h1 标题（渐变色）、副标题、日期
3. 目录：<nav class="toc">
4. 正文：<section> 分块，代码用 <pre><code>
5. footer：Howard · Powered by Claude
6. 完整文档（DOCTYPE 到 </html>）

===输出格式（严格遵守）===

先输出一行元数据 JSON，再输出分隔符，再输出 HTML。格式如下，不要有任何额外文字：

{{"filename":"英文小写连字符slug","title":"文档标题","description":"50字内中文摘要","tags":["标签1"],"date":"{today}"}}
===HTML_START===
<!DOCTYPE html>
...完整HTML...
</html>

tags 只能从以下选择 1-3 个：Tools / Workflow / AI / DevOps / Network / Dev / Security

===待处理 Markdown===

{md_content}"""


# ── 调用 Claude CLI ────────────────────────────────────────────────────────────

JSON_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "filename":     {"type": "string"},
        "title":        {"type": "string"},
        "description":  {"type": "string"},
        "tags":         {"type": "array", "items": {"type": "string"}},
        "date":         {"type": "string"},
        "html_content": {"type": "string"}
    },
    "required": ["filename", "title", "description", "tags", "date", "html_content"]
})

def call_claude(prompt: str) -> dict:
    """调用 claude -p，解析元数据 JSON + HTML 分离格式的输出。"""
    cmd = [
        "claude", "-p",
        "--output-format", "json",
        "--no-session-persistence",
    ]
    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=240
    )

    if result.returncode != 0:
        raise RuntimeError(f"claude 调用失败:\n{result.stderr.strip()}")

    outer = json.loads(result.stdout)
    raw = outer.get("result", "").strip()
    if not raw:
        raise ValueError(f"Claude 返回为空，完整输出：{result.stdout[:300]}")

    # 分离元数据 JSON 和 HTML
    separator = "===HTML_START==="
    if separator not in raw:
        raise ValueError(f"输出缺少分隔符，无法解析。前300字符：{raw[:300]}")

    meta_part, html_part = raw.split(separator, 1)

    # 解析元数据（去掉可能的 ```json 包裹）
    meta_str = meta_part.strip()
    if meta_str.startswith("```"):
        meta_str = meta_str.split("```")[1]
        if meta_str.startswith("json"):
            meta_str = meta_str[4:]
        meta_str = meta_str.strip()

    meta = json.loads(meta_str)
    meta["html_content"] = html_part.strip()
    return meta


# ── 更新 index.html ───────────────────────────────────────────────────────────

def update_index(filename: str, title: str, description: str, tags: list, date_str: str):
    content = INDEX_HTML.read_text(encoding="utf-8")

    # 检查是否已存在同名条目
    if f'href="{filename}.html"' in content:
        print(f"  ⚠ index.html 中已存在 {filename}.html，跳过插入")
        return

    tags_html = "\n        ".join(
        f'<span class="doc-tag {TAG_CLASS.get(t, "tools")}">{t}</span>'
        for t in tags
    )

    card = f"""
    <a class="doc-card" href="{filename}.html">
      <div class="doc-meta">
        {tags_html}
        <span class="doc-date">{date_str}</span>
      </div>
      <div class="doc-title">{title}</div>
      <div class="doc-desc">{description}</div>
    </a>
"""

    # 插入到 docs-grid 的最后一个卡片之后、</div> 之前
    marker = "\n  </div>\n  <div class=\"footer\">"
    if marker not in content:
        raise RuntimeError("index.html 结构不符合预期，找不到插入点")

    new_content = content.replace(marker, card + marker, 1)
    INDEX_HTML.write_text(new_content, encoding="utf-8")
    print(f"  ✓ index.html 已更新")


# ── 主流程 ────────────────────────────────────────────────────────────────────

def process(md_path: Path) -> dict:
    print(f"  📖 读取文件 {md_path.name}")
    md_content = md_path.read_text(encoding="utf-8")
    today = date.today().isoformat()
    css = read_template_css()

    print(f"  🤖 调用 Claude（脱敏 + 转换 HTML）...")
    prompt = build_prompt(md_content, today, css)
    data = call_claude(prompt)

    # 验证必要字段
    for key in ["filename", "title", "description", "tags", "date", "html_content"]:
        if key not in data:
            raise ValueError(f"Claude 返回缺少字段: {key}")

    # 写出 HTML 文件（已存在则拒绝，防止覆盖）
    html_path = BASE_DIR / f"{data['filename']}.html"
    if html_path.exists():
        raise FileExistsError(
            f"{html_path.name} 已存在，跳过（如需覆盖请先手动删除该文件）"
        )
    html_path.write_text(data["html_content"], encoding="utf-8")
    print(f"  ✓ 已生成 {html_path.name}")

    # 更新 index
    update_index(data["filename"], data["title"], data["description"], data["tags"], data["date"])

    # Git commit + push → 自动更新 GitHub Pages
    git_push(data["filename"], data["title"])

    return data


# ── Git 自动推送 ──────────────────────────────────────────────────────────────

def git_push(filename: str, title: str):
    print(f"  📤 推送到 GitHub...")
    cmds = [
        ["git", "-C", str(BASE_DIR), "add", f"{filename}.html", "index.html"],
        ["git", "-C", str(BASE_DIR), "commit", "-m", f"Add doc: {title}"],
        ["git", "-C", str(BASE_DIR), "push"],
    ]
    for cmd in cmds:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"git 命令失败: {' '.join(cmd)}\n{r.stderr.strip()}")
    print(f"  ✓ 已推送，GitHub Pages 将在约 30 秒后更新")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python3 process_doc.py <文件路径.md>")
        sys.exit(1)

    md_file = Path(sys.argv[1])
    if not md_file.exists():
        print(f"文件不存在: {md_file}")
        sys.exit(1)

    try:
        result = process(md_file)
        print(f"\n✅ 完成: {result['title']}")
        print(f"   文件: {result['filename']}.html")
        print(f"   标签: {', '.join(result['tags'])}")
    except Exception as e:
        print(f"\n❌ 处理失败: {e}")
        sys.exit(1)
