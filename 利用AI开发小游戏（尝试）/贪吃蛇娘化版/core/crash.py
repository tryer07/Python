# -*- coding: utf-8 -*-
"""
core/crash.py —— 崩溃兜底

打包成 windowed exe（console=False）后，任何未捕获异常都会让程序「静默闪退」，
玩家看不到任何信息，开发者也无从排查。这里做两件事：

  1. 把完整 traceback 追加写到 exe 同目录的 crash.log（源码运行时写在项目根）；
  2. 弹一个系统消息框，显示错误摘要 + 日志路径，而不是直接消失。

日志是「追加」模式，历次崩溃都留痕，方便对比。
"""

import os
import sys
import time
import traceback


def log_path():
    """crash.log 的绝对路径：exe 旁边（frozen）或项目根（源码）。"""
    from settings import BASE_DIR
    return os.path.join(BASE_DIR, "crash.log")


def _write_log(text):
    try:
        with open(log_path(), "a", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        # 连日志都写不了（磁盘满/无权限）也不能再抛，避免二次崩溃
        pass


def _msgbox(title, msg):
    """Windows 原生错误弹窗；非 Windows 或调用失败时静默跳过。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        # 0x10 = MB_ICONERROR，0x1000 = MB_SYSTEMMODAL（保证弹在最前）
        ctypes.windll.user32.MessageBoxW(0, str(msg), str(title), 0x10 | 0x1000)
    except Exception:
        pass


def _header(context):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "",
        "=" * 60,
        f"崩溃时间 : {ts}",
        f"上下文   : {context or '(未提供)'}",
        f"Python   : {sys.version.split()[0]}",
        f"打包运行 : {bool(getattr(sys, 'frozen', False))}",
        f"可执行文件: {sys.executable}",
        "=" * 60,
    ]
    return "\n".join(lines) + "\n"


def _tb_text(exc):
    if exc is not None:
        return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return traceback.format_exc()


def _summary(tb):
    """取 traceback 最后一行（异常类型 + 消息）作为弹窗摘要。"""
    for line in reversed(tb.strip().splitlines()):
        line = line.strip()
        if line:
            return line
    return "未知错误"


def report_crash(exc=None, context=""):
    """记录一次崩溃：写日志 + 弹窗。不会自己退出，由调用方决定后续。"""
    tb = _tb_text(exc)
    _write_log(_header(context) + tb + "\n")
    _msgbox(
        "贪吃蛇娘化版 · 出错了",
        "游戏遇到未处理的异常。\n\n"
        f"错误摘要：{_summary(tb)}\n\n"
        f"完整日志已写到：\n{log_path()}\n\n"
        "把该文件内容发给开发者，可快速定位问题。",
    )


def install_excepthook():
    """兜住任何漏网的未捕获异常（包括 pygame 主循环之外的）。"""
    def _hook(etype, value, tb):
        text = "".join(traceback.format_exception(etype, value, tb))
        _write_log(_header("sys.excepthook") + text + "\n")
        _msgbox(
            "贪吃蛇娘化版 · 出错了",
            "游戏崩溃了。\n\n"
            f"错误摘要：{_summary(text)}\n\n"
            f"完整日志已写到：\n{log_path()}",
        )

    sys.excepthook = _hook
