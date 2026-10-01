# -*- coding: utf-8 -*-
"""
tools/selfcheck.py —— 静态自检

不开游戏窗口，先把项目扫一遍：
  1. 语法是否能编译（相当于 py_compile）
  2. 每个模块引用了 settings 里不存在的名字？ -> 直接报出来
  3. 代码里写到的素材路径，文件到底在不在？
  4. JSON 配置是否合法

跑它比一上来就启动游戏快得多，能提前抓到大部分低级错误。
"""

import ast
import json
import os
import py_compile
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(BASE, "assets")

SKIP_DIRS = {"__pycache__", "build", "dist", ".workbuddy", "tools"}

errors = []
warnings = []
info = []


def iter_py_files():
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f)


# ---------------------------------------------------------------- 1. 语法
def check_syntax():
    n = 0
    for path in iter_py_files():
        n += 1
        try:
            src = open(path, encoding="utf-8").read()
            compile(src, path, "exec")
        except SyntaxError as e:
            errors.append(f"[语法错误] {os.path.relpath(path, BASE)} 第{e.lineno}行: {e.msg}")
        except UnicodeDecodeError as e:
            errors.append(f"[编码错误] {os.path.relpath(path, BASE)}: {e}")
    info.append(f"语法检查：扫描 {n} 个 py 文件")


# ---------------------------------------------- 2. settings 名字是否都存在
def collect_settings_names():
    path = os.path.join(BASE, "settings.py")
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
    return names


def check_settings_imports():
    valid = collect_settings_names()
    for path in iter_py_files():
        rel = os.path.relpath(path, BASE)
        if rel == "settings.py":
            continue
        try:
            tree = ast.parse(open(path, encoding="utf-8").read())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "settings":
                for alias in node.names:
                    if alias.name not in valid:
                        errors.append(
                            f"[settings 无此配置] {rel} 第{node.lineno}行 引用了 "
                            f"settings.{alias.name}，但 settings.py 里没有定义"
                        )
    info.append(f"配置引用检查：settings.py 共导出 {len(valid)} 个配置项")


# ------------------------------------------------ 3. 未定义名字（漏 import）
def check_undefined_names():
    """
    抓"用了没导入的名字"。

    为什么必须查这个：项目里 settings 的常量有两种写法 —— 开头的
    `from settings import CELL_SIZE` 和函数里的 `import settings as S`
    然后 `S.CELL_SIZE`。写代码时两边混用，就会出现某个分支里用了裸的
    CELL_SIZE 但顶部没导入。这种错**编译期查不出来**，只有那行代码
    真的被执行到才崩 —— 而且是运行到一半、进了某个技能分支才崩。
    所以用"所有局部名都赋值的 AST 遍历"来近似判定。
    """
    for path in iter_py_files():
        rel = os.path.relpath(path, BASE)
        try:
            tree = ast.parse(open(path, encoding="utf-8").read())
        except SyntaxError:
            continue

        # 收集模块级与所有函数内的绑定名、以及所有属性访问的名字（宽松放行）
        bound = set(dir(__builtins__)) | {"self", "cls", "__name__", "__file__"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, (ast.Store, ast.Del)):
                    bound.add(node.id)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bound.add(node.name)
            elif isinstance(node, ast.arg):
                bound.add(node.arg)
            elif isinstance(node, ast.alias):
                # from X import a, b  /  import x as y —— 都要算绑定
                bound.add((node.asname or node.name).split(".")[0])
            elif isinstance(node, ast.ExceptHandler) and node.name:
                bound.add(node.name)
            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                bound.update(node.names)
            elif isinstance(node, ast.comprehension) and isinstance(node.target, ast.Name):
                bound.add(node.target.id)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    bound.add((a.asname or a.name).split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    bound.add(a.asname or a.name)

        # 模块内定义的所有函数/类，供函数间互相调用
        local_defs = {n.name for n in ast.walk(tree)
                      if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        bound |= local_defs

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id not in bound:
                    errors.append(
                        f"[名字未定义] {rel} 第{node.lineno}行 使用了 '{node.id}'，"
                        f"但它没有被导入或赋值（漏了 import？）"
                    )
    info.append("未定义名字检查：完成")


# ------------------------------------------------------ 4. 素材路径是否真实
def check_assets():
    found = set()
    for path in iter_py_files():
        try:
            src = open(path, encoding="utf-8").read()
        except UnicodeDecodeError:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                v = node.value
                if any(v.startswith(p) for p in
                       ("characters/", "backgrounds/", "items/", "ui/", "effects/")):
                    if v.endswith(".png") or v.endswith(".jpg"):
                        found.add(v)

    # 也扫 JSON 配置里的素材路径
    data_dir = os.path.join(BASE, "data")
    if os.path.isdir(data_dir):
        for f in os.listdir(data_dir):
            if f.endswith(".json"):
                try:
                    obj = json.load(open(os.path.join(data_dir, f), encoding="utf-8"))
                except (json.JSONDecodeError, IOError):
                    continue
                for v in _walk_strings(obj):
                    if v and any(v.startswith(p) for p in
                                 ("characters/", "backgrounds/", "items/", "ui/", "effects/")):
                        found.add(v)

    missing = []
    for rel in sorted(found):
        if not os.path.exists(os.path.join(ASSETS, rel.replace("/", os.sep))):
            missing.append(rel)

    if missing:
        for m in missing:
            warnings.append(f"[素材缺失] {m} —— 游戏里会显示紫色占位块")
    info.append(f"素材检查：引用 {len(found)} 个路径，缺失 {len(missing)} 个")
    return found, missing


def _walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v)


# ------------------------------------------------------------ 4. JSON 校验
def check_json():
    data_dir = os.path.join(BASE, "data")
    if not os.path.isdir(data_dir):
        warnings.append("[配置缺失] data/ 目录不存在")
        return
    for f in sorted(os.listdir(data_dir)):
        if not f.endswith(".json"):
            continue
        p = os.path.join(data_dir, f)
        try:
            json.load(open(p, encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"[JSON 格式错误] data/{f}: {e}")
    info.append("JSON 校验：完成")


# ---------------------------------------------------------------- 输出
def main():
    print("=" * 62)
    print(" SnakeGirl 项目自检")
    print("=" * 62)

    check_syntax()
    check_settings_imports()
    check_json()
    check_assets()
    check_undefined_names()

    for line in info:
        print("  ·", line)

    if warnings:
        print("\n--- 提醒（不影响运行） ---")
        for w in warnings:
            print("  !", w)

    if errors:
        print("\n--- 错误（必须修） ---")
        for e in errors:
            print("  X", e)
        print(f"\n共 {len(errors)} 个错误")
        return 1

    print("\n未发现阻塞性问题。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
