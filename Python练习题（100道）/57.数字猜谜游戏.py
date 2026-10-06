#编写一个程序，实现数字猜谜并测试反应速度。该程序会生成一个0到99之间的随机数字供用户猜测，通过实时反馈引导用户直至猜中。同时程序会记录用户猜测耗时，并在游戏结束时提供表现反馈

# 猜数字游戏（按 57 题要求优化：0-99 随机数、记录猜测耗时、结束提供表现反馈）

import random
import time

random_num = random.randint(0, 99)  # 随机生成一个 0 到 99 的随机数

print('欢迎来到猜数字游戏！我想好了一个 0 到 99 之间的数字，猜猜看！')

start_time = time.time()  # 记录游戏开始的时间
count = 0                 # 记录猜测次数

while True:

    num = int(input('请输入你猜的数字：'))
    count += 1  # 每猜一次，计数器加 1

    if num > random_num:
        print('猜大了')
    elif num < random_num:
        print('猜小了')
    else:
        end_time = time.time()  # 猜中的时刻
        total_time = round(end_time - start_time, 2)

        print(f'恭喜！猜对了，答案就是 {random_num}')
        print(f'你一共猜了 {count} 次，总耗时：{total_time} 秒')

        # 根据用时和次数给出发表现反馈
        if total_time <= 30 and count <= 7:
            print('表现反馈：太厉害了，简直是猜神！')
        elif total_time <= 60 and count <= 15:
            print('表现反馈：不错哦，稳扎稳打！')
        else:
            print('表现反馈：重在参与，下次一定更快！')

        break

# Deleted:print('随机生成的数字是：',random_num)