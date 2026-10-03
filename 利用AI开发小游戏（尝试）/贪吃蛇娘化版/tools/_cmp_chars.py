# -*- coding: utf-8 -*-
"""临时对比脚本：以薄荷为基准，盘点潮汐/樱落的角色设计完整度差异。"""
import json, os, sys

ROOT = r"D:\Python\Python项目存放点\利用AI开发小游戏（尝试）\贪吃蛇娘化版"
sys.stdout.reconfigure(encoding="utf-8")

with open(os.path.join(ROOT, "data", "characters.json"), encoding="utf-8") as f:
    data = json.load(f)
_list = data if isinstance(data, list) else data["characters"]
chars = {c["id"]: c for c in _list}
print("全部角色 id:", [(cid, (c.get("profile") or {}).get("name")) for cid, c in chars.items()])

ids = ["lamia_mint", "lamia_tide", "sakura"]
# 1) 顶层键对比
base_keys = set(chars["lamia_mint"].keys())
for cid in ids:
    c = chars[cid]
    missing = base_keys - set(c.keys())
    extra = set(c.keys()) - base_keys
    print(f"=== {cid} ===")
    print("  顶层键数:", len(c.keys()), "| 相对薄荷缺:", missing or "无", "| 多:", extra or "无")
    fh = c.get("full_human") or {}
    print("  full_human: has_img=", bool(fh.get("img")), " human_scene=", fh.get("scene"),
          " poses键=", sorted(fh.keys()))
    sk = c.get("skills") or []
    print(f"  主动技能 {len(sk)}:", [(s.get("id"), s.get("name"), bool(s.get("desc"))) for s in sk])
    pv = c.get("passives") or []
    print(f"  被动 {len(pv)}:", [(p.get("id"), bool(p.get("desc"))) for p in pv])
    pr = c.get("profile") or {}
    print("  profile: keys=", sorted(pr.keys()))
    print("    name=", pr.get("name"), " title=", pr.get("title"), " cv=", pr.get("cv"),
          " tags=", len(pr.get("tags") or []), " desc_len=", len(pr.get("desc") or ""),
          " stats=", len(pr.get("stats") or []))
    poses = c.get("poses") or {}
    print("  poses(蛇形态):", {k: len(v) for k, v in poses.items()})
    ranged = c.get("ranged")
    print("  ranged普攻块:", "有" if ranged else "无")
    melee = c.get("melee_fx") or c.get("melee")
    print("  melee_fx块:", "有" if melee else "无")

# 2) 素材目录对比
print("\n=== 素材目录 ===")
for cid in ids:
    d = os.path.join(ROOT, "assets", "characters", cid)
    if not os.path.isdir(d):
        print(f"{cid}: 目录不存在!")
        continue
    pngs = sorted(x for x in os.listdir(d) if x.endswith(".png") and not x.startswith("_"))
    subdirs = sorted(x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)) and not x.startswith("_"))
    print(f"{cid}: png({len(pngs)})={pngs}")
    print(f"   子目录: {subdirs}")

# 3) 专属场景素材
print("\n=== 专属场景素材 ===")
for cid in ids:
    fh = chars[cid].get("full_human") or {}
    sc = fh.get("scene")
    if sc:
        p = os.path.join(ROOT, "assets", "characters", cid, sc)
        print(f"{cid}: {sc} 存在={os.path.isfile(p)}")
    else:
        print(f"{cid}: 无专属场景配置")

# 4) 特效素材（技能/普攻）
print("\n=== 特效贴图 ===")
fx_dir = os.path.join(ROOT, "assets", "effects")
for sub in sorted(os.listdir(fx_dir)):
    sp = os.path.join(fx_dir, sub)
    if not os.path.isdir(sp):
        continue
    hits = sorted(x for x in os.listdir(sp) if any(cid in x for cid in ids))
    if hits:
        print(f"effects/{sub}: {hits}")

# 5) 抽卡/编队/剧情等外围接线
print("\n=== 外围接线（gacha/levels/scenes/story） ===")
for fn in ["gacha.json", "levels.json", "scenes.json", "story.json"]:
    p = os.path.join(ROOT, "data", fn)
    if not os.path.isfile(p):
        continue
    raw = open(p, encoding="utf-8").read()
    row = {cid: raw.count(f'"{cid}"') for cid in ids}
    print(f"{fn}: {row}")

# 6) 音频
print("\n=== 角色语音/音频 ===")
au_dir = os.path.join(ROOT, "assets", "audio")
if os.path.isdir(au_dir):
    for base, dirs, files in os.walk(au_dir):
        for cid in ids:
            hits = [x for x in files if cid in x.lower()]
            if hits:
                print(os.path.relpath(base, au_dir), hits)
