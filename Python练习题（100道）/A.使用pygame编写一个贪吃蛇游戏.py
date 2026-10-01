# 使用pygame编写一个贪吃蛇游戏

import pygame
import random
import sys

# 初始化pygame
pygame.init()

# ==================== 游戏配置 ====================
WINDOW_WIDTH = 640
WINDOW_HEIGHT = 540
CELL_SIZE = 20
FPS = 8

# 颜色定义（R, G, B）
COLOR_BG = (30, 30, 46)
COLOR_GRID = (40, 40, 58)
COLOR_SNAKE_HEAD = (0, 230, 118)
COLOR_SNAKE_BODY = (0, 200, 83)
COLOR_SNAKE_OUTLINE = (0, 150, 60)
COLOR_FOOD = (255, 82, 82)
COLOR_FOOD_OUTLINE = (200, 50, 50)
COLOR_TEXT = (255, 255, 255)
COLOR_SCORE = (189, 189, 189)
COLOR_GAME_OVER = (255, 82, 82)
COLOR_TITLE = (0, 230, 118)
COLOR_KEY_HINT = (100, 200, 255)
COLOR_PAUSE = (255, 193, 7)

# 方向常量
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

# ==================== 创建窗口 ====================
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("贪吃蛇游戏")
clock = pygame.time.Clock()

# 字体设置
font_title = pygame.font.SysFont("Microsoft YaHei", 40, bold=True)
font_score = pygame.font.SysFont("Microsoft YaHei", 22)
font_game_over = pygame.font.SysFont("Microsoft YaHei", 46, bold=True)
font_hint = pygame.font.SysFont("Microsoft YaHei", 20)
font_controls = pygame.font.SysFont("Microsoft YaHei", 18)
font_section = pygame.font.SysFont("Microsoft YaHei", 20, bold=True)


# ==================== 游戏函数 ====================

# 随机生成食物位置（不与蛇身重叠）
def spawn_food(snake_body):
    while True:
        pos = (
            random.randint(0, WINDOW_WIDTH // CELL_SIZE - 1) * CELL_SIZE,
            random.randint(0, WINDOW_HEIGHT // CELL_SIZE - 1) * CELL_SIZE
        )
        if pos not in snake_body:
            return pos


# 绘制网格背景
def draw_grid():
    for x in range(0, WINDOW_WIDTH, CELL_SIZE):
        pygame.draw.line(screen, COLOR_GRID, (x, 0), (x, WINDOW_HEIGHT))
    for y in range(0, WINDOW_HEIGHT, CELL_SIZE):
        pygame.draw.line(screen, COLOR_GRID, (0, y), (WINDOW_WIDTH, y))


# 绘制圆角蛇身
def draw_snake(snake_body, current_direction):
    for i, segment in enumerate(snake_body):
        rect = pygame.Rect(segment[0], segment[1], CELL_SIZE, CELL_SIZE)
        if i == 0:
            pygame.draw.rect(screen, COLOR_SNAKE_HEAD, rect, border_radius=6)
            pygame.draw.rect(screen, COLOR_SNAKE_OUTLINE, rect, width=2, border_radius=6)
            eye_size = 3
            cx, cy = rect.center
            if current_direction == RIGHT:
                eye1 = (cx + 4, cy - 4)
                eye2 = (cx + 4, cy + 4)
            elif current_direction == LEFT:
                eye1 = (cx - 4, cy - 4)
                eye2 = (cx - 4, cy + 4)
            elif current_direction == UP:
                eye1 = (cx - 4, cy - 4)
                eye2 = (cx + 4, cy - 4)
            else:
                eye1 = (cx - 4, cy + 4)
                eye2 = (cx + 4, cy + 4)
            pygame.draw.circle(screen, (0, 0, 0), eye1, eye_size)
            pygame.draw.circle(screen, (0, 0, 0), eye2, eye_size)
        else:
            fade = max(0.4, 1.0 - i * 0.03)
            color = (
                int(COLOR_SNAKE_BODY[0] * fade),
                int(COLOR_SNAKE_BODY[1] * fade),
                int(COLOR_SNAKE_BODY[2] * fade)
            )
            pygame.draw.rect(screen, color, rect, border_radius=4)
            pygame.draw.rect(screen, COLOR_SNAKE_OUTLINE, rect, width=1, border_radius=4)


# 绘制食物（带发光效果）
def draw_food(food_pos):
    rect = pygame.Rect(food_pos[0], food_pos[1], CELL_SIZE, CELL_SIZE)
    center = rect.center
    pygame.draw.circle(screen, (80, 30, 30), center, CELL_SIZE // 2 + 4)
    pygame.draw.circle(screen, COLOR_FOOD, center, CELL_SIZE // 2)
    pygame.draw.circle(screen, COLOR_FOOD_OUTLINE, center, CELL_SIZE // 2, width=2)
    pygame.draw.circle(screen, (255, 200, 200), (center[0] - 3, center[1] - 3), 2)


# 绘制分数
def draw_score(score):
    score_text = font_score.render(f"分数：{score}", True, COLOR_SCORE)
    screen.blit(score_text, (10, 10))
    pause_text = font_controls.render("P - 暂停", True, COLOR_SCORE)
    screen.blit(pause_text, (WINDOW_WIDTH - 100, 12))


# 绘制开始界面（操作说明）
def draw_start_screen():
    screen.fill(COLOR_BG)
    draw_grid()

    # 游戏标题
    title = font_title.render("贪吃蛇", True, COLOR_TITLE)
    title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 50))
    screen.blit(title, title_rect)

    # 分割线
    pygame.draw.line(screen, COLOR_GRID, (100, 80), (WINDOW_WIDTH - 100, 80), 2)

    # 操作说明标题
    section1 = font_section.render("【 操作说明 】", True, COLOR_TEXT)
    section1_rect = section1.get_rect(center=(WINDOW_WIDTH // 2, 108))
    screen.blit(section1, section1_rect)

    # 按键说明列表
    controls = [
        ("↑ ↓ ← →  或  W A S D", "控制蛇的移动方向"),
        ("P", "暂停 / 继续游戏"),
        ("R", "重新开始游戏"),
        ("ESC", "退出游戏"),
    ]

    y_offset = 138
    for keys, desc in controls:
        key_text = font_controls.render(keys, True, COLOR_KEY_HINT)
        key_rect = key_text.get_rect(midright=(WINDOW_WIDTH // 2 - 20, y_offset))
        screen.blit(key_text, key_rect)
        desc_text = font_controls.render(desc, True, COLOR_SCORE)
        desc_rect = desc_text.get_rect(midleft=(WINDOW_WIDTH // 2 + 20, y_offset))
        screen.blit(desc_text, desc_rect)
        y_offset += 32

    # 游戏规则标题
    y_offset += 10
    section2 = font_section.render("【 游戏规则 】", True, COLOR_TEXT)
    section2_rect = section2.get_rect(center=(WINDOW_WIDTH // 2, y_offset))
    screen.blit(section2, section2_rect)

    # 规则说明
    rules = [
        "吃到红色食物 → 蛇身变长，分数 +10",
        "撞到墙壁 → 游戏结束",
        "撞到自己 → 游戏结束",
        "不允许 180° 掉头",
    ]

    y_offset += 30
    for rule in rules:
        rule_text = font_controls.render(rule, True, COLOR_SCORE)
        rule_rect = rule_text.get_rect(center=(WINDOW_WIDTH // 2, y_offset))
        screen.blit(rule_text, rule_rect)
        y_offset += 28

    # 开始提示（闪烁效果）
    if (pygame.time.get_ticks() // 500) % 2 == 0:
        start_hint = font_hint.render("按 空格键 开始游戏", True, COLOR_TITLE)
        start_rect = start_hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 35))
        screen.blit(start_hint, start_rect)

    pygame.display.flip()


# 绘制暂停画面
def draw_pause_screen(snake_body, food_pos, score, current_direction):
    screen.fill(COLOR_BG)
    draw_grid()
    draw_food(food_pos)
    draw_snake(snake_body, current_direction)
    draw_score(score)

    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.set_alpha(120)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    pause_title = font_game_over.render("已暂停", True, COLOR_PAUSE)
    pause_rect = pause_title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30))
    screen.blit(pause_title, pause_rect)

    hint_text = font_hint.render("按 P 继续游戏", True, COLOR_TEXT)
    hint_rect = hint_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 25))
    screen.blit(hint_text, hint_rect)

    quit_text = font_controls.render("按 ESC 退出 | 按 R 重新开始", True, COLOR_SCORE)
    quit_rect = quit_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 60))
    screen.blit(quit_text, quit_rect)

    pygame.display.flip()


# 绘制游戏结束画面
def draw_game_over_screen(snake_body, food_pos, score, current_direction):
    screen.fill(COLOR_BG)
    draw_grid()
    draw_food(food_pos)
    draw_snake(snake_body, current_direction)
    draw_score(score)

    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.set_alpha(150)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    text_game_over = font_game_over.render("游戏结束", True, COLOR_GAME_OVER)
    text_rect = text_game_over.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40))
    screen.blit(text_game_over, text_rect)

    text_score = font_hint.render(f"最终分数：{score}", True, COLOR_TEXT)
    text_score_rect = text_score.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20))
    screen.blit(text_score, text_score_rect)

    text_hint = font_hint.render("按 R 重新开始 | 按 ESC 退出", True, COLOR_SCORE)
    text_hint_rect = text_hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 60))
    screen.blit(text_hint, text_hint_rect)

    pygame.display.flip()


# ==================== 游戏主逻辑 ====================

# 游戏状态枚举
STATE_START = "start"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_GAME_OVER = "game_over"


def run_game():
    # 初始化游戏状态
    state = STATE_START
    snake_body = []
    food_pos = (0, 0)
    current_direction = RIGHT
    direction_queue = []
    score = 0

    while True:
        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if state == STATE_START:
                    if event.key == pygame.K_SPACE:
                        snake_body = [
                            (CELL_SIZE * 5, CELL_SIZE * 13),
                            (CELL_SIZE * 4, CELL_SIZE * 13),
                            (CELL_SIZE * 3, CELL_SIZE * 13),
                        ]
                        current_direction = RIGHT
                        direction_queue = []
                        food_pos = spawn_food(snake_body)
                        score = 0
                        state = STATE_PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

                elif state == STATE_PLAYING:
                    if event.key == pygame.K_p:
                        state = STATE_PAUSED
                    elif event.key == pygame.K_r:
                        snake_body = [
                            (CELL_SIZE * 5, CELL_SIZE * 13),
                            (CELL_SIZE * 4, CELL_SIZE * 13),
                            (CELL_SIZE * 3, CELL_SIZE * 13),
                        ]
                        current_direction = RIGHT
                        direction_queue = []
                        food_pos = spawn_food(snake_body)
                        score = 0
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

                elif state == STATE_PAUSED:
                    if event.key == pygame.K_p:
                        state = STATE_PLAYING
                    elif event.key == pygame.K_r:
                        snake_body = [
                            (CELL_SIZE * 5, CELL_SIZE * 13),
                            (CELL_SIZE * 4, CELL_SIZE * 13),
                            (CELL_SIZE * 3, CELL_SIZE * 13),
                        ]
                        current_direction = RIGHT
                        direction_queue = []
                        food_pos = spawn_food(snake_body)
                        score = 0
                        state = STATE_PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

                elif state == STATE_GAME_OVER:
                    if event.key == pygame.K_r:
                        snake_body = [
                            (CELL_SIZE * 5, CELL_SIZE * 13),
                            (CELL_SIZE * 4, CELL_SIZE * 13),
                            (CELL_SIZE * 3, CELL_SIZE * 13),
                        ]
                        current_direction = RIGHT
                        direction_queue = []
                        food_pos = spawn_food(snake_body)
                        score = 0
                        state = STATE_PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

        # 使用 get_pressed() 读取键盘状态（绕过输入法拦截）
        if state == STATE_PLAYING:
            keys = pygame.key.get_pressed()
            new_dir = None
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                new_dir = UP
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                new_dir = DOWN
            elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
                new_dir = LEFT
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                new_dir = RIGHT

            if new_dir is not None and new_dir != current_direction:
                opposite = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}
                if new_dir != opposite[current_direction]:
                    if not direction_queue or direction_queue[-1] != new_dir:
                        direction_queue.append(new_dir)

        # 根据状态更新和绘制
        if state == STATE_START:
            draw_start_screen()

        elif state == STATE_PLAYING:
            # 从方向队列中取出下一个方向
            if direction_queue:
                current_direction = direction_queue.pop(0)

            # 计算蛇头新位置
            head = snake_body[0]
            new_head = (head[0] + current_direction[0] * CELL_SIZE,
                        head[1] + current_direction[1] * CELL_SIZE)

            # 碰撞检测：撞墙
            if (new_head[0] < 0 or new_head[0] >= WINDOW_WIDTH or
                    new_head[1] < 0 or new_head[1] >= WINDOW_HEIGHT):
                state = STATE_GAME_OVER
            # 碰撞检测：撞到自己
            elif new_head in snake_body:
                state = STATE_GAME_OVER
            else:
                snake_body.insert(0, new_head)
                if new_head == food_pos:
                    score += 10
                    food_pos = spawn_food(snake_body)
                else:
                    snake_body.pop()

            # 绘制游戏画面
            if state == STATE_PLAYING:
                screen.fill(COLOR_BG)
                draw_grid()
                draw_food(food_pos)
                draw_snake(snake_body, current_direction)
                draw_score(score)
                pygame.display.flip()
            else:
                draw_game_over_screen(snake_body, food_pos, score, current_direction)

        elif state == STATE_PAUSED:
            draw_pause_screen(snake_body, food_pos, score, current_direction)

        elif state == STATE_GAME_OVER:
            draw_game_over_screen(snake_body, food_pos, score, current_direction)

        clock.tick(FPS)


# 启动游戏
run_game()
