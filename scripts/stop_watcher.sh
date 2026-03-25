#!/usr/bin/env bash
PIDFILE="$(dirname "$0")/../inbox/watcher.pid"

if [ ! -f "$PIDFILE" ]; then
  echo "⚠ 未找到 PID 文件，监控可能未在运行"
  exit 1
fi

PID=$(cat "$PIDFILE")
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  rm -f "$PIDFILE"
  echo "✅ 监控已停止（PID $PID）"
else
  echo "⚠ 进程 $PID 不存在，清理 PID 文件"
  rm -f "$PIDFILE"
fi
