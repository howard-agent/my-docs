#!/usr/bin/env bash
# 启动 inbox 文件监控守护进程
# 用法: ./start_watcher.sh         前台运行（可看日志）
#       ./start_watcher.sh -d      后台运行（守护进程）

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WATCHER="$SCRIPT_DIR/watcher.py"
LOGFILE="$SCRIPT_DIR/../inbox/watcher.log"
PIDFILE="$SCRIPT_DIR/../inbox/watcher.pid"

case "$1" in
  -d|--daemon)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "⚠ 监控已在运行（PID $(cat "$PIDFILE")）"
      exit 1
    fi
    nohup python3 "$WATCHER" >> "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    echo "✅ 后台监控已启动（PID $!）"
    echo "   日志: $LOGFILE"
    echo "   停止: $SCRIPT_DIR/stop_watcher.sh"
    ;;
  *)
    echo "前台运行监控（Ctrl+C 停止）..."
    python3 "$WATCHER"
    ;;
esac
