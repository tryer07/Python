# 使用tkinter编写一个贪吃蛇游戏

# 导入所需的库
from tkinter import Tk, Canvas, Label
import random

# 游戏配置参数
GAME_WIDTH = 600
GAME_HEIGHT = 400
CELL_SIZE = 20
SPEED = 100
SNAKE_COLOR = "#00FF00"
FOOD_COLOR = "#FF0000"
BG_COLOR = "#000000"
TEXT_COLOR = "#FFFFFF"

# 初始蛇身（3个格子长）
INITIAL_SNAKE = [
    [CELL_SIZE * 3, CELL_SIZE * 5],
    [CELL_SIZE * 2, CELL_SIZE * 5],
    [CELL_SIZE * 1, CELL_SIZE * 5],
]

# 初始方向：向右
INITIAL_DIRECTION = "Right"


# 创建游戏窗口
window = Tk()
window.title("贪吃蛇游戏")
window.resizable(False, False)

# 创建分数标签
score_label = Label(window, text="分数：0", font=("Consolas", 20), bg=BG_COLOR, fg=TEXT_COLOR)
score_label.pack()

# 创建画布
canvas = Canvas(window, width=GAME_WIDTH, height=GAME_HEIGHT, bg=BG_COLOR)
canvas.pack()

# 让窗口居中显示
window.update()
window_width = window.winfo_width()
window_height = window.winfo_height()
screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()
offset_x = (screen_width - window_width) // 2
offset_y = (screen_height - window_height) // 2
window.geometry(f"+{offset_x}+{offset_y}")


# 游戏状态变量
snake = [segment[:] for segment in INITIAL_SNAKE]
direction = INITIAL_DIRECTION
score = 0


# 随机生成食物位置（不与蛇身重叠）
def spawn_food():
    while True:
        food_x = random.randint(0, (GAME_WIDTH // CELL_SIZE) - 1) * CELL_SIZE
        food_y = random.randint(0, (GAME_HEIGHT // CELL_SIZE) - 1) * CELL_SIZE
        if [food_x, food_y] not in snake:
            return [food_x, food_y]


food = spawn_food()
game_running = True

# 绑定键盘方向键
def bind_keys():
    window.bind("<Left>", lambda _event: change_direction("Left"))
    window.bind("<Right>", lambda _event: change_direction("Right"))
    window.bind("<Up>", lambda _event: change_direction("Up"))
    window.bind("<Down>", lambda _event: change_direction("Down"))


# 改变蛇的移动方向（防止180度掉头）
def change_direction(new_direction):
    global direction
    opposite = {"Left": "Right", "Right": "Left", "Up": "Down", "Down": "Up"}
    if opposite.get(new_direction) != direction:
        direction = new_direction


# 绘制游戏画面
def draw():
    canvas.delete("all")

    # 绘制食物（圆形）
    canvas.create_oval(
        food[0], food[1],
        food[0] + CELL_SIZE, food[1] + CELL_SIZE,
        fill=FOOD_COLOR, outline=FOOD_COLOR
    )

    # 绘制蛇身（方形）
    for i, segment in enumerate(snake):
        canvas.create_rectangle(
            segment[0], segment[1],
            segment[0] + CELL_SIZE, segment[1] + CELL_SIZE,
            fill=SNAKE_COLOR if i == 0 else "#008000",
            outline=SNAKE_COLOR
        )


# 游戏结束
def game_over():
    global game_running
    game_running = False
    canvas.delete("all")
    canvas.create_text(
        GAME_WIDTH // 2, GAME_HEIGHT // 2 - 20,
        text="游戏结束！", font=("Microsoft YaHei", 30, "bold"), fill="#FF0000"
    )
    canvas.create_text(
        GAME_WIDTH // 2, GAME_HEIGHT // 2 + 30,
        text=f"最终分数：{score}", font=("Microsoft YaHei", 18), fill=TEXT_COLOR
    )
    canvas.create_text(
        GAME_WIDTH // 2, GAME_HEIGHT // 2 + 70,
        text="按 空格键 重新开始", font=("Microsoft YaHei", 14), fill="#AAAAAA"
    )
    window.bind("<space>", lambda _event: restart())


# 游戏主循环
def game_loop():
    global food, score, game_running

    if not game_running:
        return

    # 计算蛇头新位置
    head = snake[0][:]
    if direction == "Left":
        head[0] -= CELL_SIZE
    elif direction == "Right":
        head[0] += CELL_SIZE
    elif direction == "Up":
        head[1] -= CELL_SIZE
    elif direction == "Down":
        head[1] += CELL_SIZE

    # 将新蛇头插入蛇身
    snake.insert(0, head)

    # 判断是否吃到食物
    if head == food:
        score += 10
        score_label.config(text=f"分数：{score}")
        food = spawn_food()
    else:
        # 没吃到食物则去掉蛇尾（保持长度不变）
        snake.pop()

    # 碰撞检测：撞墙
    if (head[0] < 0 or head[0] >= GAME_WIDTH or
            head[1] < 0 or head[1] >= GAME_HEIGHT):
        game_over()
        return

    # 碰撞检测：撞到自己
    if head in snake[1:]:
        game_over()
        return

    # 重新绘制画面
    draw()

    # 定时执行下一次循环
    window.after(SPEED, game_loop)


# 重新开始游戏
def restart():
    global food, score, game_running

    # 重置游戏状态
    snake.clear()
    snake.extend([segment[:] for segment in INITIAL_SNAKE])
    direction_reset()
    score = 0
    game_running = True
    score_label.config(text="分数：0")

    # 重新绑定方向键（覆盖空格键绑定）
    bind_keys()

    # 生成食物并启动游戏循环
    food = spawn_food()
    game_loop()


# 重置方向
def direction_reset():
    global direction
    direction = INITIAL_DIRECTION


# 启动游戏
bind_keys()
game_loop()

# 进入主事件循环
window.mainloop()
