# -*- coding: utf-8 -*-
"""
tools/screenshot.py —— 无头截图

不开真实窗口，直接把每个场景渲染到离屏画布并存成 PNG。
这样我在没显示器/不方便弹窗的环境里也能检查画面。

用法：python tools/screenshot.py [场景名 ...]
不带参数就截全部场景。
"""

import os
import shutil
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")     # 无头模式
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

# 存档隔离：把 SAVES_DIR 指向临时目录，截图绝不污染真实 saves/
import core.save_manager as _sm  # noqa: E402
_TMP_SAVES = tempfile.mkdtemp(prefix="sg_shots_")
_sm.SAVES_DIR = _TMP_SAVES

OUT_DIR = os.path.join(BASE, "tools", "_shots")

# (输出名, 注册场景名, 标签)
SCENES = [
    ("battle_story", "battle", "战斗·剧情"),
    ("battle_endless", "battle", "战斗·无尽"),
    ("battle_cards", "battle", "战斗·升级选卡"),
    ("battle_party_human", "battle", "战斗·双人+人形态"),
    ("battle_party_cards", "battle", "战斗·双人双选卡"),
    ("main_menu", "main_menu", "主菜单"),
    ("level_select", "level_select", "关卡选择"),
    ("save_manager", "save_manager", "存档管理"),
    ("character_select", "character_select", "角色选择"),
    ("character_select_party", "character_select", "角色选择·双槽位"),
    ("character_detail", "character_detail", "角色详情"),
    ("character_detail_luna", "character_detail", "角色详情·月见"),
    ("character_detail_skills", "character_detail", "角色详情·技能"),
    ("character_detail_form", "character_detail", "角色详情·形态切换"),
    ("character_detail_exclusive", "character_detail", "角色详情·专属场景"),
    ("scene_select", "scene_select", "场景选择"),
    ("gacha", "gacha", "抽卡"),
    ("display_settings", "display_settings", "显示设置"),
]

# 战斗截图需要的模式（写入 game.pending_run）
PENDING_RUN = {
    "battle_story": {"mode": "story", "level": 1, "party": ["sakura"]},
    "battle_endless": {"mode": "endless", "scene": "neon_night",
                       "party": ["sakura"]},
    "battle_cards": {"mode": "endless", "scene": "campus_garden",
                     "party": ["sakura"]},
    # 1 号位放人形态已解锁的薄荷，开局即是「双人 + 人形态」画面
    "battle_party_human": {"mode": "endless", "scene": "campus_garden",
                           "party": ["lamia_mint", "sakura"]},
    "battle_party_cards": {"mode": "endless", "scene": "campus_garden",
                           "party": ["lamia_mint", "sakura"]},
}

# 详情页要展示的角色（默认 sakura；形态按钮那张要看已解锁人形态的薄荷）
# 月见是「白主体+浅底+光晕」抠图回归的重点观察对象
PENDING_CHAR = {
    "character_detail_form": "lamia_mint",
    "character_detail_luna": "lamia_luna",
    # 专属场景与人形态同门槛，用已解锁的薄荷来截
    "character_detail_exclusive": "lamia_mint",
}


def main():
    names = sys.argv[1:]
    os.makedirs(OUT_DIR, exist_ok=True)

    from core.game import Game
    # 无头 dummy 驱动报的“桌面”很小，默认窗口会被 WINDOW_SCALE 缩到 960x540，截图发糊。
    # 这里把桌面尺寸虚拟成大屏，再显式设 1080p，让渲染表面=1920x1080（scale=1.0，最清晰）。
    Game._get_desktop_size = lambda self: (2560, 1440)
    from scenes.main_menu import MainMenuScene
    from scenes.character_select import CharacterSelectScene
    from scenes.character_detail import CharacterDetailScene
    from scenes.scene_select import SceneSelectScene
    from scenes.level_select import LevelSelectScene
    from scenes.battle import BattleScene
    from scenes.gacha import GachaScene
    from scenes.display_settings import DisplaySettingsScene
    from scenes.save_manager_scene import SaveManagerScene

    game = Game()
    game.set_display(mode="windowed", resolution=(1920, 1080))
    game.register_scene("main_menu", MainMenuScene)
    game.register_scene("character_select", CharacterSelectScene)
    game.register_scene("character_detail", CharacterDetailScene)
    game.register_scene("scene_select", SceneSelectScene)
    game.register_scene("level_select", LevelSelectScene)
    game.register_scene("battle", BattleScene)
    game.register_scene("gacha", GachaScene)
    game.register_scene("display_settings", DisplaySettingsScene)
    game.register_scene("save_manager", SaveManagerScene)

    targets = [t for t in SCENES if not names or t[0] in names or t[1] in names]

    # 给抽卡一点初始星尘，方便看效果
    sm = game.save_manager
    sm.data["currency"] = 1200
    sm.data.setdefault("owned_characters", [])
    for cid in ("sakura", "lamia_mint", "lamia_tide"):
        if cid not in sm.data["owned_characters"]:
            sm.data["owned_characters"].append(cid)
    # 多解锁几关，让关卡选择页能展示 可挑战/已通关/锁定 三种状态
    sm.data["story_unlocked"] = 3
    sm.data["story_cleared"] = [1]
    # 双人出战 + 人形态解锁（薄荷强化层数达到门槛）
    for _ in range(12):
        sm.add_enhance("lamia_mint")
    sm.set_deploy_slot(1, "sakura")
    sm.set_deploy_slot(2, "lamia_mint")
    sm.set_form_pref("lamia_mint", "human")

    for out_name, scene_name, label in targets:
        # 选角页两张对照：单人编队 vs 双人编队（底部槽位徽标）
        if out_name == "character_select":
            sm.set("deploy_party", ["sakura"])
        elif out_name == "character_select_party":
            sm.set("deploy_party", ["sakura", "lamia_mint"])
        game.pending_run = PENDING_RUN.get(out_name)
        game.pending_char_id = PENDING_CHAR.get(out_name, "sakura")
        game.change_scene(scene_name)
        scene = game.current_scene
        # 角色详情页额外截一张「技能介绍」面板
        if out_name == "character_detail_skills":
            scene.panel_mode = "skills"
        # 专属场景页：切到最后一个 tab（scene_idx == len(scenes)）
        if out_name == "character_detail_exclusive":
            scene._pick_scene(len(scene.scenes))
        scene.update(1 / 60)

        # 战斗场景多跑一会儿，让蛇和怪都动起来（剧情局保留新手指引浮层）
        if scene_name == "battle":
            for _ in range(120):
                scene.update(1 / 60)
        # 抽卡场景让它真的抽一次，看结果页
        if scene_name == "gacha":
            scene._pull(10)
            for _ in range(20):
                scene.update(1 / 60)
        # 升级选卡：跑一会儿后手动打开三选一浮层，展示肉鸽卡池新特性
        if out_name == "battle_cards":
            # 先叠几次属性，让卡片预览显示「当前 → 选中后」的累计成长（而非全 0）
            mb = scene.party[scene.active_idx]
            for _ in range(2):
                scene._apply_passive("lifesteal", mb)
                scene._apply_passive("atk", mb)
            scene.card_overlay = None
            scene._open_card_overlay()
            # 保底：若随机没抽到属性卡，塞一张吸血卡进去，确保预览可见
            if not any(c.get("preview") for c in scene.card_overlay):
                lc = scene._with_preview(
                    next(c for c in scene._card_pool()
                         if c.get("stat") == "lifesteal"), mb)
                scene.card_overlay[0] = lc
        # 双人局：走一次升级，让浮层按 1 号位→2 号位 排队（截到「为 ① XX 选择」）
        if out_name == "battle_party_cards":
            scene._on_level_up(scene.snake.level + 1, 1)
            scene._open_card_overlay()

        scene.draw()
        out = os.path.join(OUT_DIR, f"{out_name}.png")
        pygame.image.save(game.render_surface, out)
        print(f"[截图] {label:10s} -> {out}")

    pygame.quit()
    shutil.rmtree(_TMP_SAVES, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
