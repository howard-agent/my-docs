#!/usr/bin/env python3
"""
处理单个 MD 文件：隐私脱敏 → 转 HTML（新建或追加）→ 更新 index.html → git push
用法: python3 process_doc.py <文件路径.md>

文件名规则：
  - 普通文件（any-name.md）→ 新建 HTML
  - session-archiver 格式（topic_YYYYMMDD.md）→ 若 topic.html 已存在则追加新章节，否则新建
"""

import re
import sys
import json
import os
import subprocess
from pathlib import Path
from datetime import date

BASE_DIR  = Path(__file__).parent.parent
INDEX_HTML = BASE_DIR / "index.html"

TAG_CLASS = {
    "Tools": "tools", "Workflow": "workflow", "AI": "ai",
    "DevOps": "dev",  "Network": "dev",       "Dev": "dev", "Security": "dev",
}

# ── CSS 模板 ──────────────────────────────────────────────────────────────────

def read_template_css() -> str:
    template = BASE_DIR / "sunflower-remote-boot-guide.html"
    if not template.exists():
        return ""
    content = template.read_text(encoding="utf-8")
    start = content.find("<style>")
    end   = content.find("</style>") + len("</style>")
    return content[start:end] if start != -1 else ""


# ── 检测是否为「追加更新」模式 ────────────────────────────────────────────────

def detect_append_target(md_path: Path) -> Path | None:
    """
    若文件名符合 topic_YYYYMMDD.md 格式，且对应 topic.html 已存在，
    返回该 HTML 路径（追加模式）；否则返回 None（新建模式）。
    """
    m = re.match(r'^(.+?)_(\d{8})\.md$', md_path.name)
    if not m:
        return None
    topic_slug = m.group(1).replace("_", "-")
    html_path  = BASE_DIR / f"{topic_slug}.html"
    return html_path if html_path.exists() else None


# ── Prompt：新建模式 ──────────────────────────────────────────────────────────

def build_create_prompt(md_content: str, today: str, css: str) -> str:
    return f"""你是技术文档处理助手。请对下方 Markdown 完成两项任务。

===任务 1：隐私脱敏===

将以下类型信息替换为占位符（技术命令、开源软件名、公开API文档中的通用字段名无需脱敏）：

**个人信息：** 真实姓名→[姓名] / 邮箱→[邮箱] / 电话→[电话] / 地址→[地址] / 账号ID→[账号ID]
**网络信息：** 内网IP→[内网IP] / 公网IP→[公网IP] / MAC→[MAC地址] / 生产域名→[域名]
**凭证信息：** 密码Token→[密钥] / API Key→[API密钥] / 序列号→[序列号]
**商业数据：** 具体金额/收入/利润/成本数字→[金额] / 毛利率等财务比率→[比率] / 订单量→[数量] / 公司内部项目名→[项目名] / 店铺名/卖家名→[店铺名] / 产品ASIN/SKU→[产品ID]
**内部路径：** 项目内部文件路径→保留相对结构但模糊化为示例路径（如 analysis/xxx.py → analysis/data_fetcher.py）
**内部API：** 非公开的内部API端点路径→[API端点]

重要：本文档用于公开发布的学习笔记。重点保留技术原理和学习心得，删除所有可追溯到具体公司、具体业务的数据。如有疑问，宁可多脱敏。

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

===输出格式（严格遵守，不要有任何额外文字）===

{{"filename":"英文小写连字符slug","title":"文档标题","description":"50字内中文摘要","tags":["标签1"],"date":"{today}"}}
===HTML_START===
<!DOCTYPE html>
...完整HTML...
</html>

tags 只能从以下选择 1-3 个：Tools / Workflow / AI / DevOps / Network / Dev / Security

===待处理 Markdown===

{md_content}"""


# ── Prompt：追加模式 ──────────────────────────────────────────────────────────

def build_append_prompt(existing_html: str, md_content: str, today: str) -> str:
    return f"""你是技术文档处理助手。下方是一个已有 HTML 文档和一份新的 Markdown 内容（新的 session 记录）。

任务：
1. 对新 Markdown 做隐私脱敏（完整规则：个人信息/网络信息/凭证/商业数据如金额利润率订单量/公司项目名/店铺名/ASIN SKU/内部文件路径/内部API端点→全部替换为占位符。保留技术原理和学习心得，删除所有可追溯到具体公司具体业务的数据）
2. 将脱敏后内容转换为一个新的 <section> 章节，日期标题为 {today}
3. 将该新 <section> 插入到已有 HTML 的 </main> 或最后一个 </section> 之前
4. 同时更新 <nav class="toc"> 目录，加入新章节的条目
5. 输出完整的更新后 HTML（不要截断）

===输出格式（只输出 HTML，不要有任何额外文字）===

===HTML_START===
<!DOCTYPE html>
...完整更新后的HTML...
</html>

===已有 HTML===
{existing_html}

===新 Markdown 内容===
{md_content}"""


# ── 调用 Claude（HTTP API 主路径 + CLI 备用）──────────────────────────────────


def _build_env() -> dict:
    """
    构建 claude 子进程的完整环境变量。
    继承当前进程环境，同时补全 HOME、代理等必须项。
    """
    env = os.environ.copy()

    # 确保 HOME 存在（systemd 下可能缺失）
    env.setdefault("HOME", str(Path.home()))

    # 确保 claude 在 PATH 里
    claude_bin = Path.home() / ".local" / "bin"
    path_dirs = env.get("PATH", "").split(":")
    if str(claude_bin) not in path_dirs:
        env["PATH"] = f"{claude_bin}:{env.get('PATH', '')}"

    # 代理：从 ~/.claude/.credentials.json 同级的 claude 进程环境读取
    # 如果当前进程已有代理就直接用，否则尝试从运行中的 claude 进程继承
    if not env.get("HTTPS_PROXY") and not env.get("https_proxy"):
        try:
            import glob
            # 找正在运行的 claude 进程的 environ
            for pid_env in glob.glob("/proc/*/environ"):
                pid_vars = open(pid_env, "rb").read().split(b"\x00")
                pid_map  = {}
                for v in pid_vars:
                    if b"=" in v:
                        k, _, val = v.partition(b"=")
                        pid_map[k.decode(errors="ignore")] = val.decode(errors="ignore")
                if "PROXY_HOST" in pid_map and "PROXY_PORT" in pid_map:
                    host = pid_map["PROXY_HOST"]
                    port = pid_map["PROXY_PORT"]
                    proxy_url = f"http://{host}:{port}"
                    env["HTTPS_PROXY"] = proxy_url
                    env["HTTP_PROXY"]  = proxy_url
                    env["https_proxy"] = proxy_url
                    env["http_proxy"]  = proxy_url
                    env.setdefault("PROXY_HOST", host)
                    env.setdefault("PROXY_PORT", port)
                    break
        except Exception:
            pass

    return env


def call_claude(prompt: str) -> str:
    """通过 claude CLI subprocess 调用，自动继承完整运行环境。"""
    cmd = ["claude", "-p", "--output-format", "json", "--no-session-persistence"]
    env = _build_env()

    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude 调用失败: {result.stderr.strip() or result.stdout[:300]}")
    outer = json.loads(result.stdout)
    if outer.get("is_error"):
        raise RuntimeError(f"claude 返回错误: {outer.get('result', '')[:200]}")
    raw = outer.get("result", "").strip()
    if not raw:
        raise ValueError(f"claude 返回为空: {result.stdout[:300]}")
    return raw


def parse_create_response(raw: str) -> dict:
    """解析新建模式的「元数据JSON + ===HTML_START=== + HTML」格式。"""
    separator = "===HTML_START==="
    if separator not in raw:
        raise ValueError(f"输出缺少分隔符。前300字符：{raw[:300]}")
    meta_str, html_part = raw.split(separator, 1)
    meta_str = meta_str.strip()
    if meta_str.startswith("```"):
        meta_str = meta_str.split("```")[1]
        if meta_str.startswith("json"):
            meta_str = meta_str[4:]
        meta_str = meta_str.strip()
    meta = json.loads(meta_str)
    meta["html_content"] = html_part.strip()
    return meta


def parse_append_response(raw: str) -> str:
    """解析追加模式的纯 HTML 输出。"""
    separator = "===HTML_START==="
    if separator in raw:
        raw = raw.split(separator, 1)[1]
    return raw.strip()


# ── index.html 操作 ───────────────────────────────────────────────────────────

def _build_card(filename: str, title: str, description: str, tags: list, date_str: str) -> str:
    tags_html = "\n        ".join(
        f'<span class="doc-tag {TAG_CLASS.get(t, "tools")}">{t}</span>' for t in tags
    )
    return f"""
    <a class="doc-card" href="{filename}.html">
      <div class="doc-meta">
        {tags_html}
        <span class="doc-date">{date_str}</span>
      </div>
      <div class="doc-title">{title}</div>
      <div class="doc-desc">{description}</div>
    </a>
"""


def _extract_card(content: str, filename: str) -> str | None:
    """从 index.html 中提取某个文件对应的完整卡片 HTML。"""
    pattern = rf'\n    <a class="doc-card" href="{re.escape(filename)}\.html">.*?</a>\n'
    m = re.search(pattern, content, re.DOTALL)
    return m.group(0) if m else None


def update_index(filename: str, title: str, description: str, tags: list, date_str: str):
    """新建：将卡片插到 docs-grid 最前面（最新在上）。"""
    content = INDEX_HTML.read_text(encoding="utf-8")
    if f'href="{filename}.html"' in content:
        print(f"  ⚠ index.html 已有 {filename}.html，跳过")
        return
    card = _build_card(filename, title, description, tags, date_str)
    marker = "<div class=\"docs-grid\">\n"
    if marker not in content:
        raise RuntimeError("index.html 结构不符合预期，找不到插入点")
    INDEX_HTML.write_text(content.replace(marker, marker + card, 1), encoding="utf-8")
    print(f"  ✓ index.html 已更新（插入首位）")


def update_index_date(filename: str, new_date: str):
    """追加模式：更新日期，并将卡片移到最前面。"""
    content = INDEX_HTML.read_text(encoding="utf-8")
    card = _extract_card(content, filename)
    if not card:
        print(f"  ⚠ index.html 未找到 {filename}.html 的卡片")
        return
    # 更新日期
    updated_card = re.sub(
        r'(<span class="doc-date">)[^<]+(</span>)',
        rf'\g<1>{new_date}\g<2>',
        card
    )
    # 移除旧卡片，插到最前面
    content = content.replace(card, "")
    marker = "<div class=\"docs-grid\">\n"
    content = content.replace(marker, marker + updated_card, 1)
    INDEX_HTML.write_text(content, encoding="utf-8")
    print(f"  ✓ index.html 卡片已移至首位，日期更新为 {new_date}")


# ── Git 推送 ──────────────────────────────────────────────────────────────────

def git_push(filename: str, commit_msg: str):
    print(f"  📤 推送到 GitHub...")
    cmds = [
        ["git", "-C", str(BASE_DIR), "add", f"{filename}.html", "index.html"],
        ["git", "-C", str(BASE_DIR), "commit", "-m", commit_msg],
        ["git", "-C", str(BASE_DIR), "push", "--porcelain"],
    ]
    for cmd in cmds:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"git 失败: {' '.join(cmd)}\n{r.stderr.strip()}")
    # 验证：检查 push 的 porcelain 输出是否包含 rejected，
    # 而不是用 git status 检查 ahead（会被其他未提交改动干扰）
    if r.returncode == 0 and "rejected" not in r.stderr:
        print(f"  ✓ 已推送，GitHub Pages 将在约 30 秒后更新")
    else:
        raise RuntimeError(f"push 失败:\n{r.stderr.strip()}")


# ── 主流程 ────────────────────────────────────────────────────────────────────

def process(md_path: Path) -> dict:
    print(f"  📖 读取文件 {md_path.name}")
    md_content = md_path.read_text(encoding="utf-8")
    today = date.today().isoformat()

    append_target = detect_append_target(md_path)

    if append_target:
        # ── 追加模式：更新已有 HTML ──
        print(f"  🔄 追加模式 → 更新 {append_target.name}")
        existing_html = append_target.read_text(encoding="utf-8")
        prompt = build_append_prompt(existing_html, md_content, today)
        raw = call_claude(prompt)
        updated_html = parse_append_response(raw)
        append_target.write_text(updated_html, encoding="utf-8")
        print(f"  ✓ {append_target.name} 已追加新章节")

        filename = append_target.stem
        update_index_date(filename, today)
        git_push(filename, f"Update doc: {append_target.stem} ({today})")
        return {"filename": filename, "title": append_target.stem, "mode": "append"}

    else:
        # ── 新建模式 ──
        css = read_template_css()
        print(f"  🤖 调用 Claude（脱敏 + 新建 HTML）...")
        prompt = build_create_prompt(md_content, today, css)
        raw = call_claude(prompt)
        data = parse_create_response(raw)

        for key in ["filename", "title", "description", "tags", "date", "html_content"]:
            if key not in data:
                raise ValueError(f"Claude 返回缺少字段: {key}")

        html_path = BASE_DIR / f"{data['filename']}.html"
        if html_path.exists():
            raise FileExistsError(f"{html_path.name} 已存在，跳过")
        html_path.write_text(data["html_content"], encoding="utf-8")
        print(f"  ✓ 已生成 {html_path.name}")

        update_index(data["filename"], data["title"], data["description"], data["tags"], data["date"])
        git_push(data["filename"], f"Add doc: {data['title']}")
        data["mode"] = "create"
        return data


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
        mode = "追加" if result.get("mode") == "append" else "新建"
        print(f"\n✅ 完成（{mode}）: {result.get('title', result['filename'])}")
    except Exception as e:
        print(f"\n❌ 处理失败: {e}")
        sys.exit(1)
