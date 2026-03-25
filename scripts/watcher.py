#!/usr/bin/env python3
"""
监控 inbox/ 文件夹，自动处理新 .md 文件。
用法: python3 watcher.py
"""

import hashlib
import time
import subprocess
import shutil
import sys
from pathlib import Path
from datetime import datetime

INBOX     = Path(__file__).parent.parent / "inbox"
PROCESSED = INBOX / "processed"
FAILED    = INBOX / "failed"
SCRIPT    = Path(__file__).parent / "process_doc.py"
POLL_SEC  = 4


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def normalize(md_path: Path) -> Path:
    """修复 Mac 拖入时产生的 .md.md 双扩展名问题。"""
    if md_path.suffix == ".md" and md_path.stem.endswith(".md"):
        fixed = md_path.with_name(md_path.stem)   # 去掉多余的 .md
        md_path.rename(fixed)
        log(f"🔧 修正双扩展名: {md_path.name} → {fixed.name}")
        return fixed
    return md_path


def load_seen_hashes() -> set:
    """从 processed/ 和 failed/ 读取已处理文件的内容 hash，跨 session 去重。"""
    hashes = set()
    for folder in (PROCESSED, FAILED):
        for f in folder.glob("*.md"):
            try:
                hashes.add(file_hash(f))
            except OSError:
                pass
    return hashes


def process_file(md_path: Path):
    log(f"📄 处理: {md_path.name}")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(md_path)],
        capture_output=False,
        text=True,
    )
    dest_dir = PROCESSED if result.returncode == 0 else FAILED
    label    = "✅ 完成" if result.returncode == 0 else "❌ 失败"

    try:
        shutil.move(str(md_path), str(dest_dir / md_path.name))
        log(f"{label}，文件已移至 inbox/{dest_dir.name}/")
    except OSError as e:
        log(f"⚠ 移动文件失败（{e}），可能已不存在")


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    FAILED.mkdir(parents=True, exist_ok=True)

    log(f"👀 开始监控 {INBOX}")
    log(f"   将 .md 文件拖入该文件夹即可自动处理")
    log(f"   按 Ctrl+C 停止\n")

    seen_names:  set = (
        {f.name for f in PROCESSED.glob("*.md")} |
        {f.name for f in FAILED.glob("*.md")}
    )
    seen_hashes: set = load_seen_hashes()

    # 忽略启动时 inbox/ 里已有的文件
    for f in INBOX.glob("*.md"):
        seen_names.add(f.name)
        log(f"⚠ 已忽略启动前存在的文件: {f.name}")

    while True:
        try:
            for md_path in sorted(INBOX.glob("*.md")):
                # 1. 修复双扩展名（.md.md → .md）
                md_path = normalize(md_path)

                # 2. 按文件名去重
                if md_path.name in seen_names:
                    continue

                # 3. 按内容 hash 去重（防止同内容改名重复提交）
                h = file_hash(md_path)
                if h in seen_hashes:
                    log(f"⚠ 跳过重复内容: {md_path.name}（与已处理文件内容相同）")
                    seen_names.add(md_path.name)
                    shutil.move(str(md_path), str(PROCESSED / md_path.name))
                    continue

                seen_names.add(md_path.name)
                seen_hashes.add(h)

                try:
                    process_file(md_path)
                except Exception as e:
                    log(f"❌ 异常: {e}")

            time.sleep(POLL_SEC)

        except KeyboardInterrupt:
            log("👋 监控已停止")
            break


if __name__ == "__main__":
    main()
