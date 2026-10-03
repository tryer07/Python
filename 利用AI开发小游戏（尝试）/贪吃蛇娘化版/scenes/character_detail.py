# -*- coding: utf-8 -*-
"""
scenes/character_detail.py —— 角色详情页

点选角页的已拥有角色进入。这里可以：
  1. 切换 4 个场景背景，看该角色在场景中的完整样子（全身立绘，蛇尾与身体一体）
  2. 点击立绘的头 / 身 / 尾触发彩蛋（台词气泡 + 音效 + 轻微动作）
  3. 查看角色背景故事 / 设定
  4. 查看强化层数（0-15，重复抽卡叠层）
  5. 设为出战 / 返回选角页
"""

import json
import math
import os
import random

import pygame

from core.scene import Scene
from core.save_manager import DETAIL_SCENE_EXCLUSIVE
from ui.button import Button
from game_logic.skills import SkillEngine
from settings import (
    ASSETS_DIR, DATA_DIR, HUMAN_FORM_ENHANCE_REQ, ROLE_NAMES, ROLE_HINTS,
    COLOR_BG, COLOR_ACCENT, COLOR_BG_LIGHT, COLOR_GOLD, COLOR_TEXT, COLOR_TEXT_DIM,
    FONT_SIZE_TITLE, FONT_SIZE_SUBTITLE, FONT_SIZE_BODY, FONT_SIZE_SMALL
)

# 属性 -> 专属场景动效主色（花瓣/光斑用，与角色设定对味）
ELEMENT_FX_COLORS = {
    "樱": (255, 168, 205), "风": (150, 232, 190), "水": (120, 200, 235),
    "月": (214, 220, 255), "火": (255, 158, 110), "星": (255, 220, 140),
}


class CharacterDetailScene(Scene):
    """角色详情场景"""

    def enter(self):
        self.assets = self.game.assets
        self.game.audio.play_bgm("menu")
        self.font_title = self.assets.get_font(self.s(FONT_SIZE_TITLE), bold=True)
        self.font_sub = self.assets.get_font(self.s(FONT_SIZE_SUBTITLE))
        self.font_body = self.assets.get_font(self.s(FONT_SIZE_BODY))
        self.font_small = self.assets.get_font(self.s(FONT_SIZE_SMALL))
        self.font_tiny = self.assets.get_font(self.s(FONT_SIZE_SMALL - 4))
        # 称号专用粗体：配渐变金 + 柔光描边，比暗淡正文醒目
        self.font_epithet = self.assets.get_font(self.s(FONT_SIZE_BODY), bold=True)

        save = self.game.save_manager
        self.owned = save.get("owned_characters", [])
        char_id = getattr(self.game, "pending_char_id", None) \
            or save.get("selected_character", "sakura")
        self.char = self._load_char(char_id)
        self.char_id = self.char.get("id", "sakura")
        self.is_owned = self.char_id in self.owned
        # 双人编队 / 人形态彩蛋（强化达标解锁）
        self.party = save.get_deploy_party()
        self.human_unlocked = save.human_form_unlocked(self.char_id)
        self.form_pref = save.get_form_pref(self.char_id)

        self.scenes = self._load_scenes()
        # 专属场景（人形态带背景原图）：约定路径 characters/<id>/human_scene.png。
        # 不进 scenes.json（那是全局战斗地图表）、也不进 characters.json
        #（技能动作设计期正被并行编辑），缺文件自动隐藏该 tab。
        self.exclusive_rel = f"characters/{self.char_id}/human_scene.png"
        if not os.path.exists(os.path.join(
                ASSETS_DIR, self.exclusive_rel.replace("/", os.sep))):
            self.exclusive_rel = None
        # 场景 tab 初值：该角色主动选过就记住并用它（含专属），否则跟随全局已选战斗场景
        self.scene_idx = self._resolve_scene_idx(save)
        self._excl_cache_key = None   # 专属场景背景层缓存键（屏幕尺寸）
        self._excl_under = None       # 垫底层：cover + 强模糊，只露在完整图两侧黑边区
        self._excl_sharp = None       # 主层：human_scene 原图 contain 完整显示
        self._excl_sharp_rect = None  # 主落矩形（彩蛋热区按它三等分）
        self._excl_fx = []            # 专属场景动效粒子（前景花瓣 + 背景光斑）
        self._excl_sprites = {}       # 动效贴图缓存（含旋转步/透明度档）
        self._excl_strips = None      # 窄留边补边：主层边缘拉伸条 [(surf, rect)]
        self._gen_bg_cache = {}       # 通用场景 背景+压暗纱 合成缓存（按屏幕/场景）
        self._lock_hint = 0.0         # 未解锁提示倒计时

        self.time = 0.0
        self.egg = None            # {"region","text","timer"}
        self.pulse = 0.0           # 点击后的动作脉冲
        self._regions = {}         # 彩蛋热区
        self.panel_mode = "story"  # 右侧面板：story=故事/强化，skills=技能介绍
        # 技能介绍页：数值表引擎 + 贴图图标缓存 + 整页预渲染画布。
        # 滚动分「目标值 / 当前值」两截：输入直接改 target，update 里让
        # skill_scroll 平滑追上，滑起来是一段动画而不是逐格跳。
        self.skill_scroll = 0.0
        self.skill_scroll_target = 0.0
        self._icon_cache = {}
        # 文字缓存：font.size() / font.render() 在本作环境下单次要 0.1~0.4ms，
        # 而详情页的文案全是静态配置。缓存后每帧命中，不再重复测量/渲染。
        self._wrap_cache = {}
        self._text_cache = {}
        self._skill_canvas = None      # 整页预渲染结果（None = 尚未构建）
        self._skill_canvas_h = 0       # 内容总高
        self._skill_view_h = 0         # 可视窗口（裁剪区）高，用于算滚动上限
        self._skill_engine = SkillEngine()
        self._skill_engine.load_kit(self.char_id)
        # 整页预渲染放在进场景时就做完（与背景/立绘的首次加载归到同一笔），
        # 这样点「技能介绍」tab 是瞬时的，不会在页内切换时顿一下。
        self._build_skill_canvas()
        # 专属场景背景层（解码 + contain + 补边）也放在进场景时做完，与技能
        # 整页预渲染归同一笔加载开销：点「专属场景」tab 是瞬时的，不会顿一下。
        if self.exclusive_rel:
            self._exclusive_layers()

        self._build_buttons()

    def exit(self):
        pass

    # ---------------------------------------------------------------- 配置
    @staticmethod
    def _read_json(filename):
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return []

    def _load_char(self, char_id):
        for ch in self._read_json("characters.json"):
            if isinstance(ch, dict) and ch.get("id") == char_id:
                return ch
        return {"id": char_id, "name": char_id, "head": "characters/sakura/head.png"}

    def _load_scenes(self):
        data = self._read_json("scenes.json")
        return [s for s in data if isinstance(s, dict) and s.get("id")] or \
            [{"id": "campus_garden", "name": "校园庭院",
              "bg": "backgrounds/campus_garden.png"}]

    # ---------------------------------------------------------------- 布局
    def _build_buttons(self):
        # 场景切换 tab（左下一排）
        self.tab_btns = []
        n = len(self.scenes)
        tw, th = self.s(150), self.s(44)
        gap = self.s(14)
        total = n * tw + (n - 1) * gap
        x0 = self.s(60)
        y = self.H - self.s(96)
        for i, sc in enumerate(self.scenes):
            b = Button(sc.get("name", "?"), x0 + i * (tw + gap), y, tw, th,
                       font_size=self.s(FONT_SIZE_SMALL - 2),
                       on_click=lambda idx=i: self._pick_scene(idx))
            self.tab_btns.append(b)
        # 专属场景 tab：排在四个场景之后；未解锁时点击只提示不切换
        if self.exclusive_rel:
            i = len(self.scenes)
            b = Button("专属场景", x0 + i * (tw + gap), y, tw, th,
                       font_size=self.s(FONT_SIZE_SMALL - 2),
                       on_click=lambda idx=i: self._pick_scene(idx))
            self.tab_btns.append(b)

        # 右侧操作按钮：两行（第一行出战槽，第二行形态/返回）
        px = self._panel_rect().x
        bw, bh = self.s(200), self.s(54)
        gap = self.s(20)
        by1 = self.H - self.s(158)
        by2 = self.H - self.s(96)
        self.slot1_btn = Button(
            "设为1号位", px + self.s(24), by1, bw, bh,
            font_size=self.s(FONT_SIZE_BODY), on_click=lambda: self._on_deploy(1))
        self.slot2_btn = Button(
            "设为2号位", px + self.s(24) + bw + gap, by1, bw, bh,
            font_size=self.s(FONT_SIZE_BODY), on_click=lambda: self._on_deploy(2))
        self.form_btn = Button(
            self._form_label(), px + self.s(24), by2, self.s(300), bh,
            font_size=self.s(FONT_SIZE_BODY), on_click=self._on_form_toggle)
        self.back_btn = Button(
            "返回", px + self.s(24) + self.s(300) + gap, by2, bw, bh,
            font_size=self.s(FONT_SIZE_BODY), on_click=self._on_back)

        # 面板顶部：角色故事 / 技能介绍 切换 tab
        pr = self._panel_rect()
        tw, th = self.s(150), self.s(42)
        ty = pr.y - th - self.s(12)
        self.story_tab = Button("角色故事", pr.x, ty, tw, th,
                                font_size=self.s(FONT_SIZE_SMALL - 2),
                                on_click=lambda: self._set_mode("story"))
        self.skill_tab = Button("技能介绍", pr.x + tw + self.s(12), ty, tw, th,
                                font_size=self.s(FONT_SIZE_SMALL - 2),
                                on_click=lambda: self._set_mode("skills"))

    def _set_mode(self, mode):
        self.panel_mode = mode
        self.game.audio.play("ui_click")

    def _panel_rect(self):
        pw = self.s(620)
        return pygame.Rect(self.W - pw - self.s(40), self.s(120),
                           pw, self.H - self.s(240))

    def _resolve_scene_idx(self, save):
        """详情页场景 tab 初值：玩家在该角色页主动选过场景就记住并复用它
        （含专属场景），没选过 / 记忆失效才回退全局已选战斗场景。"""
        pref = save.get_detail_scene(self.char_id)
        if pref == DETAIL_SCENE_EXCLUSIVE:
            return len(self.scenes) if (self.exclusive_rel
                                        and self.human_unlocked) else 0
        if isinstance(pref, str):
            for i, sc in enumerate(self.scenes):
                if sc.get("id") == pref:
                    return i
            return 0
        cur = save.get("selected_scene", "campus_garden")
        for i, sc in enumerate(self.scenes):
            if sc.get("id") == cur:
                return i
        return 0

    def _pick_scene(self, idx):
        if idx >= len(self.scenes) and not self.human_unlocked:
            # 专属场景 = 人形态内容，与人形态同属强化彩蛋，达标才开放
            self._lock_hint = 3.0
            self.game.audio.play("ui_click")
            return
        self.scene_idx = idx
        # 记住本次主动选择：下次进该角色详情页直接停在这个 tab
        key = (DETAIL_SCENE_EXCLUSIVE if idx >= len(self.scenes)
               else self.scenes[idx].get("id"))
        self.game.save_manager.set_detail_scene(self.char_id, key)
        self.game.audio.play("ui_click")

    def _on_deploy(self, slot):
        if not self.is_owned:
            return
        self.party = self.game.save_manager.set_deploy_slot(slot, self.char_id)
        self.game.audio.play("ui_click")
        self.game.change_scene("character_select")

    def _form_label(self):
        if not self.human_unlocked:
            return f"人形态 · 强化{HUMAN_FORM_ENHANCE_REQ}解锁"
        return "形态：人形态" if self.form_pref == "human" else "形态：蛇形态"

    def _on_form_toggle(self):
        """人形态彩蛋切换：未解锁只提示不生效"""
        if not self.is_owned:
            return
        if not self.human_unlocked:
            self.game.audio.play("ui_click")
            return
        nxt = "lamia" if self.form_pref == "human" else "human"
        self.form_pref = self.game.save_manager.set_form_pref(self.char_id, nxt)
        self.form_btn.text = self._form_label()
        self.game.audio.play("eat_heart")

    def _on_back(self):
        self.game.change_scene("character_select")

    # ---------------------------------------------------------------- 输入
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._on_back()
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for region, rect in self._regions.items():
                    if rect and rect.collidepoint(event.pos):
                        self._trigger_egg(region)
                        break
            if self.panel_mode == "skills":
                # 浏览技能介绍：滚轮为主，方向键 / 翻页键 / Home / End 兼顾无滚轮场景
                if event.type == pygame.MOUSEWHEEL:
                    self._scroll_by(-event.y * self.s(88))
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_DOWN:
                        self._scroll_by(self.s(110))
                    elif event.key == pygame.K_UP:
                        self._scroll_by(-self.s(110))
                    elif event.key == pygame.K_PAGEDOWN:
                        self._scroll_by(self._skill_view_h * 0.85)
                    elif event.key == pygame.K_PAGEUP:
                        self._scroll_by(-self._skill_view_h * 0.85)
                    elif event.key == pygame.K_HOME:
                        self.skill_scroll_target = 0.0
                    elif event.key == pygame.K_END:
                        self.skill_scroll_target = float(self._skill_max_scroll())
            for b in self.tab_btns:
                b.handle_event(event)
            self.slot1_btn.handle_event(event)
            self.slot2_btn.handle_event(event)
            self.form_btn.handle_event(event)
            self.back_btn.handle_event(event)
            self.story_tab.handle_event(event)
            self.skill_tab.handle_event(event)

    def _trigger_egg(self, region):
        lines = (self.char.get("egg_lines") or {}).get(region) or []
        if not lines:
            return
        text = random.choice(lines)
        self.egg = {"region": region, "text": text, "timer": 2.6}
        self.pulse = 1.0
        self.game.audio.play("eat_heart")

    def update(self, dt):
        self.time += dt
        self.pulse = max(0.0, self.pulse - dt * 2.2)
        self._lock_hint = max(0.0, self._lock_hint - dt)
        # 技能页平滑滚动：指数趋近目标值（帧率无关），滚轮一动就是顺滑位移
        diff = self.skill_scroll_target - self.skill_scroll
        if abs(diff) < 0.5:
            self.skill_scroll = self.skill_scroll_target
        else:
            self.skill_scroll += diff * (1.0 - math.exp(-15.0 * dt))
        if self.egg:
            self.egg["timer"] -= dt
            if self.egg["timer"] <= 0:
                self.egg = None
        # 专属场景动效：只在专属 tab 下推进，离开即清空（回来重新撒点）
        if self.exclusive_rel is not None and self.scene_idx >= len(self.scenes):
            if not self._excl_fx:
                self._seed_excl_fx()
            self._update_excl_fx(dt)
        elif self._excl_fx:
            self._excl_fx = []

    # ---------------------------------------------------------------- 绘制
    def draw(self):
        screen = self.screen
        screen.fill(COLOR_BG)

        exclusive = self.exclusive_rel is not None \
            and self.scene_idx >= len(self.scenes)
        if exclusive:
            # 专属场景：human_scene.png 带背景原图 contain 等比完整显示（不裁切，
            # 场景与人物全部内容放出来），两侧留边用同图强模糊垫底衔接；
            # 人物由背景插画自带，不再叠独立立绘（避免双人）；
            # 动效 = 背景光斑（back）+ 前景花瓣（front）撒在画面上。
            self._draw_exclusive_bg(screen)
            self._draw_exclusive_fx(screen, back=True)
            self._set_exclusive_regions()
            self._draw_exclusive_fx(screen, back=False)
            sc_name = "专属场景"
        else:
            sc = self.scenes[self.scene_idx]
            bg_path = sc.get("bg") or "backgrounds/campus_garden.png"
            screen.blit(self._generic_bg(bg_path), (0, 0))
            # 通用场景：背景 + 压暗纱之后画全身立绘（专属分支里是 force_human）
            self._draw_pose(screen)
            sc_name = sc.get("name", "")

        # 标题
        t = self._text(self.char.get("name", "?"), self.font_title, COLOR_ACCENT)
        screen.blit(t, t.get_rect(center=(self.W // 2, self.s(70))))
        if self._lock_hint > 0:
            sub = f"人形态与专属场景一同在强化 {HUMAN_FORM_ENHANCE_REQ} 解锁"
        else:
            sub = f"{sc_name} · 点击她的头 / 身 / 尾试试"
        t = self._text(sub, self.font_small, COLOR_TEXT_DIM)
        screen.blit(t, t.get_rect(center=(self.W // 2, self.s(112))))

        self._draw_panel(screen)
        self._draw_egg(screen)

        for b in self.tab_btns:
            b.draw(screen)
        self.slot1_btn.draw(screen)
        self.slot2_btn.draw(screen)
        self.form_btn.draw(screen)
        self.back_btn.draw(screen)
        self.story_tab.draw(screen)
        self.skill_tab.draw(screen)

    # ---- 全身立绘展示：蛇尾与身体一体，无拼接缝 ----
    def _draw_pose(self, screen):
        pose_cx = int(self.W * 0.30)
        anchor_bottom = int(self.H * 0.86)

        path = self.char.get("full") or self.char.get("head") \
            or "characters/sakura/head.png"
        if self.form_pref == "human" and self.char.get("full_human"):
            path = self.char["full_human"]
        img = self.assets.get_scaled(path, height=self.s(680))
        # 点击脉冲：轻微放大 + 摆动
        if self.pulse > 0:
            k = 1.0 + math.sin(self.pulse * math.pi) * 0.03
            img = pygame.transform.smoothscale(
                img, (int(img.get_width() * k), int(img.get_height() * k)))
        bob = math.sin(self.time * 1.6) * self.s(4)
        rect = img.get_rect(center=(pose_cx, int(anchor_bottom - img.get_height() // 2 + bob)))
        screen.blit(img, rect)

        # 彩蛋热区：全身立绘竖直三等分 = 头 / 身 / 尾
        third = rect.height // 3
        self._regions = {
            "head": pygame.Rect(rect.x, rect.y, rect.w, third),
            "body": pygame.Rect(rect.x, rect.y + third, rect.w, third),
            "tail": pygame.Rect(rect.x, rect.y + third * 2,
                                rect.w, rect.height - third * 2),
        }

    # ---- 专属场景：原图完整显示（contain）+ 模糊垫边 + 动效粒子 ----
    def _exclusive_layers(self):
        """专属场景背景层（按屏幕尺寸缓存）：
        sharp = human_scene.png 原图 contain 等比缩放居中，任何窗口分辨率 /
        全屏下场景与人物都完整可见（旧版 cover 裁切会切掉头尾）；
        under = 同图 cover 放大 + 强模糊 + 比屏幕大 12%，铺在黑边区做衔接垫底，
        超宽 / 超窄窗口下屏幕不会被死黑块割裂。
        """
        key = (self.W, self.H)
        if self._excl_cache_key == key and self._excl_sharp is not None:
            return self._excl_under, self._excl_sharp, self._excl_sharp_rect
        base = self.assets.get_image(self.exclusive_rel)
        w, h = base.get_size()
        # 主层：contain 等比，完整放进来居中
        k = min(self.W / w, self.H / h)
        sw, sh = max(1, round(w * k)), max(1, round(h * k))
        sharp = pygame.transform.smoothscale(base, (sw, sh))
        rect = sharp.get_rect(center=(self.W // 2, self.H // 2))
        # 留边衔接分两档：窄边（<=6%，16:9 宽图在 16:9 屏的常态）用主层边缘
        # 像素拉伸补边，每帧省一次全屏垫底 blit 和几十 MB 缓存；宽边（超宽 /
        # 超窄窗口）回退同图 cover + 强模糊垫底，内容永不裁切。
        strips = self._edge_strips(sharp, rect)
        under = None
        if strips is None:
            tw, th = int(self.W * 1.12), int(self.H * 1.12)
            ku = max(tw / w, th / h)
            under = pygame.transform.smoothscale(
                base, (max(1, round(w * ku)), max(1, round(h * ku))))
            under = under.subsurface(pygame.Rect(
                (under.get_width() - tw) // 2, (under.get_height() - th) // 2,
                tw, th)).copy()
            under = pygame.transform.smoothscale(under, (tw // 8, th // 8))
            under = pygame.transform.smoothscale(under, (tw, th))
        # 压暗纱在缓存构建时烘进各层（旧写法每帧建全屏半透明画布再 blit，
        # 是已知的隐蔽掉帧源）。
        self._bake_veil(sharp, 56)
        if under is not None:
            self._bake_veil(under, 56)
        else:
            for surf, _r in strips:
                self._bake_veil(surf, 56)
        self._excl_cache_key = key
        self._excl_under = under
        self._excl_strips = strips
        self._excl_sharp = sharp
        self._excl_sharp_rect = rect
        return under, sharp, rect

    def _edge_strips(self, sharp, rect):
        """窄留边补边：主层上下（或左右）边缘像素条拉伸铺满留边区（补边不碰
        画面内容）。留边超过 6% 时拉伸观感差，返回 None 由调用方回退模糊垫底。"""
        sw, sh = sharp.get_size()
        strips = []
        if rect.height < self.H:
            top, bot = rect.y, self.H - rect.bottom
            if max(top, bot) > self.H * 0.06:
                return None
            src_h = max(2, sh // 64)
            if top > 0:
                strips.append((self._soft_strip(pygame.transform.smoothscale(
                    sharp.subsurface(pygame.Rect(0, 0, sw, src_h)), (sw, top))),
                    pygame.Rect(rect.x, 0, sw, top)))
            if bot > 0:
                strips.append((self._soft_strip(pygame.transform.smoothscale(
                    sharp.subsurface(pygame.Rect(0, sh - src_h, sw, src_h)), (sw, bot))),
                    pygame.Rect(rect.x, rect.bottom, sw, bot)))
        elif rect.width < self.W:
            left, right = rect.x, self.W - rect.right
            if max(left, right) > self.W * 0.06:
                return None
            src_w = max(2, sw // 64)
            if left > 0:
                strips.append((self._soft_strip(pygame.transform.smoothscale(
                    sharp.subsurface(pygame.Rect(0, 0, src_w, sh)), (left, sh))),
                    pygame.Rect(0, rect.y, left, sh)))
            if right > 0:
                strips.append((self._soft_strip(pygame.transform.smoothscale(
                    sharp.subsurface(pygame.Rect(sw - src_w, 0, src_w, sh)), (right, sh))),
                    pygame.Rect(rect.right, rect.y, right, sh)))
        return strips

    @staticmethod
    def _soft_strip(surf):
        """补边条两级缩放柔化（免单向拉伸出现条纹感），缓存时一次性。"""
        w, h = surf.get_size()
        d = pygame.transform.smoothscale(surf, (max(1, w // 4), max(1, h // 4)))
        return pygame.transform.smoothscale(d, (w, h))

    @staticmethod
    def _bake_veil(surf, alpha):
        """压暗纱烘进图层（缓存构建时一次性），取代每帧全屏半透明 blit。"""
        veil = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        veil.fill((14, 12, 22, alpha))
        surf.blit(veil, (0, 0))

    def _generic_bg(self, bg_path):
        """通用场景 背景+压暗纱 合成层（按屏幕尺寸/场景缓存）：背景是静态的，
        合成一次每帧只做一次不透明 blit。"""
        key = (self.W, self.H, bg_path)
        hit = self._gen_bg_cache.get(key)
        if hit is not None:
            return hit
        bg = self.assets.get_scaled(bg_path, width=self.W)
        comp = pygame.Surface((self.W, self.H))
        comp.blit(bg, (0, self.s(-40)))
        self._bake_veil(comp, 178)
        if len(self._gen_bg_cache) > 8:
            self._gen_bg_cache.clear()
        self._gen_bg_cache[key] = comp
        return comp

    def _draw_exclusive_bg(self, screen):
        """宽留边垫底慢漂移（呼吸感）/ 窄留边补边 -> 完整图居中。
        压暗纱已在缓存时烘进各层，每帧不再全屏半透明 blit。"""
        under, sharp, rect = self._exclusive_layers()
        if under is not None:
            mx = (under.get_width() - self.W) // 2
            my = (under.get_height() - self.H) // 2
            ox = int(math.sin(self.time * 0.10) * mx * 0.8)
            oy = int(math.cos(self.time * 0.07) * my * 0.8)
            screen.blit(under, (-mx + ox, -my + oy))
        else:
            for surf, r in self._excl_strips:
                screen.blit(surf, r)
        screen.blit(sharp, rect)

    def _set_exclusive_regions(self):
        """专属场景彩蛋热区：人物在背景插画里居中，按完整显示矩形竖直三等分
        = 头 / 身 / 尾；热区跟随 contain 矩形，任何分辨率下都点得准。"""
        r = self._excl_sharp_rect or pygame.Rect(0, 0, self.W, self.H)
        third = r.height // 3
        self._regions = {
            "head": pygame.Rect(r.x, r.y, r.w, third),
            "body": pygame.Rect(r.x, r.y + third, r.w, third),
            "tail": pygame.Rect(r.x, r.y + third * 2, r.w, r.height - third * 2),
        }

    def _seed_excl_fx(self):
        """撒动效粒子：前景花瓣（飘落+摇摆+自旋）+ 背景光斑（上浮+闪烁）。"""
        self._excl_fx = []
        for _ in range(26):
            self._excl_fx.append({
                "kind": "petal",
                "x0": random.uniform(0, self.W),
                "y": random.uniform(-self.H * 0.1, self.H),
                "vy": random.uniform(0.05, 0.12) * self.H,
                "amp": random.uniform(0.01, 0.04) * self.W,
                "freq": random.uniform(0.5, 1.2),
                "phase": random.uniform(0, 6.283),
                "rot": random.uniform(0, 360),
                "vr": random.uniform(-40, 40),
                "size": random.choice((self.s(14), self.s(20), self.s(26))),
            })
        for _ in range(22):
            self._excl_fx.append({
                "kind": "glow",
                "x": random.uniform(0, self.W),
                "y": random.uniform(self.H * 0.25, self.H),
                "vy": random.uniform(0.02, 0.06) * self.H,
                "freq": random.uniform(0.8, 1.6),
                "phase": random.uniform(0, 6.283),
                "size": random.choice((self.s(10), self.s(16), self.s(22))),
            })

    def _update_excl_fx(self, dt):
        """推进动效粒子；出界从另一侧回填，数量恒定不增不减。"""
        for p in self._excl_fx:
            if p["kind"] == "petal":
                p["y"] += p["vy"] * dt
                p["rot"] = (p["rot"] + p["vr"] * dt) % 360.0
                if p["y"] > self.H + self.s(30):
                    p["y"] = -self.s(30)
                    p["x0"] = random.uniform(0, self.W)
            else:
                p["y"] -= p["vy"] * dt
                if p["y"] < self.H * 0.15:
                    p["y"] = self.H * 1.02
                    p["x"] = random.uniform(0, self.W)

    def _fx_sprite(self, kind, size):
        """动效基础贴图（缓存）：glow=径向柔光斑，petal=椭圆花瓣。"""
        size = max(4, int(size))
        key = (kind, size)
        hit = self._excl_sprites.get(key)
        if hit is not None:
            return hit
        color = ELEMENT_FX_COLORS.get(self.char.get("element", ""), COLOR_ACCENT)
        if kind == "glow":
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            r = size // 2
            for i in range(r, 0, -1):
                a = int(150 * (i / r) ** 2)
                pygame.draw.circle(surf, (*color, a), (r, r), i)
        else:
            w, h = size, max(3, int(size * 0.62))
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, (*color, 200), (0, 0, w, h))
            pygame.draw.ellipse(surf, (255, 255, 255, 90),
                                (w // 4, h // 4, w // 2, h // 2))
        if len(self._excl_sprites) > 256:
            self._excl_sprites.clear()
        self._excl_sprites[key] = surf
        return surf

    def _fx_sprite_rot(self, size, step):
        """花瓣旋转步贴图（15° 一步缓存）：避免每帧 rotozoom 重采样掉帧。"""
        key = ("petal_rot", int(size), step)
        hit = self._excl_sprites.get(key)
        if hit is not None:
            return hit
        spr = pygame.transform.rotozoom(self._fx_sprite("petal", size),
                                        step * 15, 1.0)
        self._excl_sprites[key] = spr
        return spr

    def _fx_sprite_alpha(self, size, level):
        """光斑透明度档贴图（4 档缓存）：闪烁靠换档，不靠每帧 set_alpha。"""
        key = ("glow_a", int(size), level)
        hit = self._excl_sprites.get(key)
        if hit is not None:
            return hit
        spr = self._fx_sprite("glow", size).copy()
        spr.set_alpha(80 + level * 30)
        self._excl_sprites[key] = spr
        return spr

    def _draw_exclusive_fx(self, screen, back):
        """动效层：back=背景光斑（立绘后），front=前景花瓣（立绘前）。"""
        want = "glow" if back else "petal"
        for p in self._excl_fx:
            if p["kind"] != want:
                continue
            if want == "petal":
                x = p["x0"] + math.sin(self.time * p["freq"] + p["phase"]) * p["amp"]
                spr = self._fx_sprite_rot(p["size"], int(p["rot"] // 15) % 24)
                screen.blit(spr, (int(x - spr.get_width() // 2),
                                  int(p["y"] - spr.get_height() // 2)))
            else:
                tw = math.sin(self.time * p["freq"] + p["phase"])
                lv = int((tw * 0.5 + 0.5) * 3.999)
                spr = self._fx_sprite_alpha(p["size"], lv)
                screen.blit(spr, (int(p["x"] - spr.get_width() // 2),
                                  int(p["y"] - spr.get_height() // 2)))

    # ---- 右侧信息面板 ----
    def _draw_panel(self, screen):
        pr = self._panel_rect()
        panel = pygame.Surface((pr.w, pr.h), pygame.SRCALPHA)
        panel.fill((*COLOR_BG_LIGHT, 226))
        screen.blit(panel, pr.topleft)
        pygame.draw.rect(screen, COLOR_ACCENT, pr, 2, border_radius=self.s(14))

        x = pr.x + self.s(28)
        y = pr.y + self.s(30)
        w = pr.w - self.s(56)

        rarity = self.char.get("rarity", "N")
        role = self.char.get("role", "hybrid")
        t = self._text(
            f"{self.char.get('name', '?')}  ·  {rarity}  ·  "
            f"{self.char.get('element', '无')}  ·  "
            f"{ROLE_NAMES.get(role, '全能')}", self.font_sub, COLOR_GOLD)
        screen.blit(t, (x, y))
        y += self.s(40)

        # 角色称号：渐变金 + 柔光描边，做成醒目的「徽章」样式；
        # 技能名不在此显示（归下方「技能介绍」tab），避免与首个技能重名混淆
        y += self._draw_epithet(screen, x, y)

        t = self._text(
            f"成长 · {self.char.get('growth', '-')}",
            self.font_small, COLOR_ACCENT)
        screen.blit(t, (x, y))
        y += self.s(34)

        # 职业定位一句话（法师/刺客/坦克的取舍）
        hint = ROLE_HINTS.get(role, "")
        if hint:
            t = self._text(hint, self.font_small, COLOR_TEXT_DIM)
            screen.blit(t, (x, y))
            y += self.s(34)
        else:
            y += self.s(6)

        # 背景故事
        if self.panel_mode == "skills":
            self._draw_skill_list(screen, x, y, w)
            return

        t = self._text("背景故事", self.font_body, COLOR_TEXT)
        screen.blit(t, (x, y))
        y += self.s(32)
        for line in self._wrap(self.char.get("story", ""), self.font_small, w):
            screen.blit(self._text(line, self.font_small, COLOR_TEXT_DIM), (x, y))
            y += self.s(26)
        y += self.s(14)

        # 强化层数
        layer = self.game.save_manager.get_enhance(self.char_id)
        t = self._text(f"强化层数  {layer} / 15", self.font_body, COLOR_GOLD)
        screen.blit(t, (x, y))
        y += self.s(34)
        pip = self.s(26)
        gap = self.s(8)
        for i in range(15):
            rx = x + i * (pip + gap)
            rect = pygame.Rect(rx, y, pip, self.s(14))
            if i < layer:
                pygame.draw.rect(screen, COLOR_GOLD, rect, border_radius=4)
            else:
                pygame.draw.rect(screen, (60, 56, 80), rect, border_radius=4)
        y += self.s(30)
        t = self._text("重复抽到该角色 +1 层（加外观与数值）· 满 15 层后返还星尘",
                       self.font_small, COLOR_TEXT_DIM)
        screen.blit(t, (x, y))
        y += self.s(30)

        # 出战槽位 / 出战形态（人形态为强化彩蛋）
        if self.char_id in self.party:
            slot_txt = f"{self.party.index(self.char_id) + 1} 号位"
        else:
            slot_txt = "未设置"
        form_txt = "人形态" if self.form_pref == "human" else "蛇形态"
        t = self._text(f"出战：{slot_txt} · 形态：{form_txt}",
                       self.font_body, COLOR_ACCENT)
        screen.blit(t, (x, y))
        y += self.s(34)

        # 形态自由切换：解锁后本页按钮与战斗内 V 键都能随时切，两处同源
        if self.human_unlocked:
            tip = "形态可自由切换：本页「形态」按钮 · 战斗内 V 键（纯外观）"
        else:
            tip = (f"强化到 {HUMAN_FORM_ENHANCE_REQ} 层解锁人形态"
                   f"（当前 {layer} 层），解锁后可自由切换")
        t = self._text(tip, self.font_small, COLOR_TEXT_DIM)
        screen.blit(t, (x, y))
        y += self.s(30)

        if not self.is_owned:
            t = self._text("尚未解锁 · 前往抽卡获得", self.font_small,
                           (230, 110, 120))
            screen.blit(t, (x, y))

    def _draw_epithet(self, screen, x, y):
        """角色称号：渐变金主体 + 深琥珀柔光描边 + 「」装饰。

        比原先的暗淡小字醒目得多，但字号仍小于顶部角色名，层级不乱。
        上下各留一段显式留白（徽章与邻行不挤在一起），返回本行占用
        高度（含留白），调用方据此推进 y，杜绝与上下文字重叠。
        整块渐变+描边只渲染一次并缓存。
        """
        title = (self.char.get("title") or "").strip()
        if not title:
            return 0
        pad_top = self.s(18)
        pad_bot = self.s(28)
        surf = self._epithet_surf(f"「 {title} 」", self.font_epithet)
        screen.blit(surf, (x, y + pad_top))
        return pad_top + surf.get_height() + pad_bot

    def _epithet_surf(self, text, font):
        """渐变金字 + 柔光描边，渲染一次缓存（键含文本/字号）。"""
        key = ("epithet", text, font.get_height())
        hit = self._text_cache.get(key)
        if hit is not None:
            return hit
        txt = font.render(text, True, (255, 255, 255))
        w, h = txt.get_size()
        # 字体自带行距偏紧，「」和金字上下几乎顶到边：先把渐变严格按
        # 字形裁好，再上下垫一段透明边，字就不贴边（垫边必须是透明，
        # 否则渐变底会残留成贯穿全宽的色条）
        pad = max(2, font.get_height() // 6)
        gh = h + pad * 2
        grad = pygame.Surface((w, h), pygame.SRCALPHA)
        top, bot = (255, 246, 198), (233, 165, 46)
        for i in range(h):
            t = i / max(1, h - 1)
            c = tuple(int(top[k] + (bot[k] - top[k]) * t) for k in range(3))
            pygame.draw.line(grad, c, (0, i), (w, i))
        # 用白字的字形 alpha 把渐变裁成文字形状
        grad.blit(txt, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        grad_pad = pygame.Surface((w, gh), pygame.SRCALPHA)
        grad_pad.blit(grad, (0, pad))
        off = max(2, self.s(3))
        glow = font.render(text, True, (190, 125, 30))
        out = pygame.Surface((w + off * 2, gh + off * 2), pygame.SRCALPHA)
        r2 = off * off
        for dx in range(-off, off + 1):
            for dy in range(-off, off + 1):
                if dx * dx + dy * dy <= r2:
                    out.blit(glow, (off + dx, off + dy + pad))
        out.blit(grad_pad, (off, off))
        if len(self._text_cache) > 400:
            self._text_cache.clear()
        self._text_cache[key] = out
        return out

    def _skill_icon(self, sid, box):
        """技能专属贴图图标（等比缩进 box 见方）；缺图返回 None（该角色无专属贴图）。"""
        if not sid:
            return None
        box = max(8, int(box))
        key = (sid, box)
        if key in self._icon_cache:
            return self._icon_cache[key]
        rel = f"effects/skills/{sid}.png"
        full = os.path.join(ASSETS_DIR, rel.replace("/", os.sep))
        img = None
        if os.path.exists(full):
            try:
                base = self.assets.get_image(rel)
                bw, bh = base.get_size()
                k = min(box / bw, box / bh)
                img = pygame.transform.smoothscale(
                    base, (max(1, int(bw * k)), max(1, int(bh * k))))
            except Exception:
                img = None
        self._icon_cache[key] = img
        return img

    def _skill_kit(self):
        """解析 characters.json 的 kit：返回 (主动技能列表, 被动列表)。"""
        kit = self.char.get("kit") or {}
        actives = kit.get("actives")
        if not isinstance(actives, list) or not actives:
            one = kit.get("active")
            actives = [one] if isinstance(one, dict) else []
        return ([a for a in actives if isinstance(a, dict)],
                [p for p in (kit.get("passives") or []) if isinstance(p, dict)])

    def _skill_max_scroll(self):
        """滚动上限 = 内容总高 - 可视高（内容不足一屏时为 0，不可滚）。"""
        return max(0, int(self._skill_canvas_h - self._skill_view_h))

    def _scroll_by(self, delta):
        self.skill_scroll_target = max(
            0.0, min(float(self._skill_max_scroll()),
                     self.skill_scroll_target + float(delta)))

    def _paint_skill_canvas(self, height):
        """把整份技能介绍画到一张 height 高的画布上，返回 (画布, 实际内容高)。
        画布坐标以裁剪区左上角为原点，滚动时只需改 blit 的源区域偏移。"""
        pr = self._panel_rect()
        cw = pr.w - self.s(20)                  # 裁剪区宽（面板左右各内缩 10）
        x = self.s(18)                          # 面板内缩 28 - 裁剪内缩 10
        wrap_w = pr.w - self.s(56) - self.s(12)
        actives, passives = self._skill_kit()
        eng = self._skill_engine
        cv = pygame.Surface((max(1, cw), max(self.s(64), int(height))),
                            pygame.SRCALPHA)
        cy = 0
        for a in actives:
            sid = a.get("id")
            color = tuple((a.get("color") or [255, 255, 255])[:3])
            icon = self._skill_icon(sid, self.s(46))
            hx = x
            if icon is not None:
                cv.blit(icon, icon.get_rect(midleft=(hx, cy + self.s(13))))
                hx += self.s(52)
            head = self._text(f"[{a.get('key', 1)}]  {a.get('name', '')}",
                              self.font_body, color)
            cv.blit(head, (hx, cy))
            cy += head.get_height() + self.s(3)
            for line in self._wrap(a.get("desc", ""), self.font_small, wrap_w):
                cv.blit(self._text(line, self.font_small, COLOR_TEXT_DIM),
                        (x + self.s(12), cy))
                cy += self.s(22)
            for label, vals in eng.stat_columns(sid):
                txt = f"{label}  " + " / ".join(vals)
                cv.blit(self._text(txt, self.font_tiny, COLOR_GOLD),
                        (x + self.s(12), cy))
                cy += self.s(19)
            cy += self.s(12)
            pygame.draw.line(cv, (255, 255, 255, 26), (x, cy), (cw - x, cy), 1)
            cy += self.s(12)
        for p in passives:
            color = tuple((p.get("color") or [255, 255, 255])[:3])
            head = self._text(f"[被动]  {p.get('name', '')}", self.font_body, color)
            cv.blit(head, (x, cy))
            cy += head.get_height() + self.s(3)
            for line in self._wrap(p.get("desc", ""), self.font_small, wrap_w):
                cv.blit(self._text(line, self.font_small, COLOR_TEXT_DIM),
                        (x + self.s(12), cy))
                cy += self.s(22)
            cy += self.s(10)
        return cv, cy

    def _build_skill_canvas(self):
        """整页只渲染一次并缓存，滚动时只做一次 blit(area=...)。

        技能介绍现在每个主动都是「长文案 + Lv0-3 数值表」，如果每帧都
        重新折行（逐字 font.size）+ 重跑数值管线 + 渲染上百个文字面，
        滚轮一动就明显掉帧。预渲染后滚动开销恒定，与内容多少无关。
        进页时才构建（而非 enter），角色故事页不白白付这笔开销。
        """
        actives, passives = self._skill_kit()
        # 按「主动≈图标+标题+5 行文案+6 行数值、被动≈标题+3 行文案」估高，
        # 估得越准越好：估高了白占内存，估矮了会触发下面那次重画。
        est = self.s(60) + len(actives) * self.s(300) + len(passives) * self.s(150)
        cv, cy = self._paint_skill_canvas(est)
        if cy > cv.get_height():            # 估算不够高：按实际内容重画一次
            cv, cy = self._paint_skill_canvas(cy + self.s(80))
        cv = cv.subsurface(pygame.Rect(0, 0, cv.get_width(),
                                      max(1, min(cy, cv.get_height())))).copy()
        self._skill_canvas = cv
        self._skill_canvas_h = cv.get_height()
        self.skill_scroll = max(0.0, min(self.skill_scroll,
                                        float(self._skill_max_scroll())))
        self.skill_scroll_target = self.skill_scroll

    def _draw_skill_list(self, screen, x, y, w):
        """技能介绍面板：5 主动（贴图图标/键位/名字/详细说明/全等级数值）+ 全部被动。
        内容整页预渲染后裁剪滚动（见 _build_skill_canvas），数值与局内生效值同源。"""
        pr = self._panel_rect()
        # 标题一行、操作提示一行：旧版把两段挤在同一行，长标题会压到右对齐的提示
        t = self._text("技能介绍（1-5 主动 · 被动常驻）", self.font_body,
                       COLOR_GOLD)
        screen.blit(t, (x, y))
        hint = self._text("数值列 = Lv0/1/2/3 · 滚轮 / ↑↓ / PgUp·PgDn 浏览",
                          self.font_tiny, COLOR_TEXT_DIM)
        screen.blit(hint, (x, y + t.get_height() + self.s(4)))
        y += t.get_height() + hint.get_height() + self.s(12)

        # 底边避开面板内的"设为1/2号位"按钮行，滚动内容不再钻到按钮下面
        bottom = min(pr.bottom - self.s(14), self.slot1_btn.rect.y - self.s(8))
        clip = pygame.Rect(pr.x + self.s(10), y, pr.w - self.s(20),
                           bottom - y)
        self._skill_view_h = clip.h
        if self._skill_canvas is None:
            self._build_skill_canvas()
        cv = self._skill_canvas
        maxs = self._skill_max_scroll()
        top = max(0, min(int(self.skill_scroll), maxs))
        screen.set_clip(clip)
        area_h = min(clip.h, cv.get_height() - top)
        if area_h > 0:
            screen.blit(cv, (clip.x, clip.y),
                        pygame.Rect(0, top, cv.get_width(), area_h))
        screen.set_clip(None)
        if maxs > 0:
            self._draw_skill_scrollbar(screen, clip, top, maxs)

    def _draw_skill_scrollbar(self, screen, clip, top, maxs):
        """右侧细滚动条：仅内容超出可视区时出现，提示玩家下面还有东西。"""
        bw = max(2, self.s(5))
        track = pygame.Rect(clip.right - bw - self.s(3), clip.y + self.s(3),
                            bw, max(self.s(20), clip.h - self.s(6)))
        bar = pygame.Surface((track.w, track.h), pygame.SRCALPHA)
        bar.fill((255, 255, 255, 26))
        th = max(self.s(26),
                 int(track.h * clip.h / max(1, self._skill_canvas_h)))
        ty = int((track.h - th) * (top / max(1, maxs)))
        pygame.draw.rect(bar, (*COLOR_ACCENT, 205),
                         pygame.Rect(0, ty, track.w, th), border_radius=bw // 2)
        screen.blit(bar, track.topleft)

    def _draw_egg(self, screen):
        if not self.egg:
            return
        head_rect = self._regions.get("head")
        if not head_rect:
            return
        text = self.egg["text"]
        # 气泡
        pad = self.s(18)
        surf = self.font_body.render(text, True, COLOR_TEXT)
        bw = surf.get_width() + pad * 2
        bh = surf.get_height() + pad * 2
        bx = head_rect.centerx - bw // 2
        by = max(self.s(140), head_rect.top - bh - self.s(20))
        bubble = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bubble.fill((250, 244, 250, 236))
        self.screen.blit(bubble, (bx, by))
        pygame.draw.rect(self.screen, COLOR_ACCENT, (bx, by, bw, bh), 2,
                         border_radius=self.s(10))
        self.screen.blit(surf, (bx + pad, by + pad))

    # ---------------------------------------------------------------- 工具
    def _text(self, text, font, color):
        """渲染并缓存一段文字（同文本+同字号+同颜色只渲染一次）。

        font.render() 单次 0.1~0.4ms，面板上十几行静态文案逐帧重渲染
        就是好几毫秒。返回的是缓存共享面，调用方不要对它 set_alpha。
        """
        key = ("txt", text, font.get_height(), tuple(color))
        hit = self._text_cache.get(key)
        if hit is not None:
            return hit
        if len(self._text_cache) > 400:
            self._text_cache.clear()
        surf = font.render(text, True, color)
        self._text_cache[key] = surf
        return surf

    def _wrap(self, text, font, max_w):
        """中文按字折行（结果缓存 + 二分找断点）。

        两个提速点，都是详情页掉帧的真实大头：
          1. 旧写法逐字 font.size(cur + ch)，一行 30 字就要 30 次测量，
             整页文案下来每帧上千次 × 0.17ms ≈ 上百毫秒；改成二分后
             每行只要 log2(字数) 次（~7 次）。
          2. 文案全是静态配置，折行结果按 (文本, 字号, 宽) 缓存，
             第二帧开始直接命中，一次 size 也不用调。
        """
        text = text or ""
        key = ("wrap", text, font.get_height(), max_w)
        hit = self._wrap_cache.get(key)
        if hit is not None:
            return hit
        lines = []
        rest = text
        while rest:
            if font.size(rest)[0] <= max_w:
                lines.append(rest)
                rest = ""
                break
            lo, hi, cut = 1, len(rest) - 1, 1
            while lo <= hi:
                mid = (lo + hi) // 2
                if font.size(rest[:mid])[0] <= max_w:
                    cut = mid
                    lo = mid + 1
                else:
                    hi = mid - 1
            lines.append(rest[:cut])
            rest = rest[cut:]
        if len(self._wrap_cache) > 240:
            self._wrap_cache.clear()
        self._wrap_cache[key] = lines
        return lines or [""]
