# 编写一个程序，实现简单秒表功能：
# 按下回车开始计时，再按一次回车停止并显示计时结果；
# 显示结果后给用户两个选择：再次计时 / 结束程序

# 导入time模块，用于处理时间相关的任务

import time

# 外层while循环支撑"多次计时"的整体流程，直到用户选择结束才break退出

while True:

    print('\n===== 简单秒表 =====')

    # 第一次回车：开始计时，并记录起始时间

    input('按回车开始计时...')
    start_time = time.time()

    # 第二次回车：停止计时（input会一直等待，回车一按立即向下执行）

    input('计时中... 按回车停止并查看结果 >>> ')

    # 记录结束时间，算出总耗时并保留两位小数

    end_time = time.time()
    total_time = round(end_time - start_time, 2)

    # 显示本次计时结果

    print(f'\n本次经过的时间为：{total_time} 秒')

    # 给用户两个选择：y 再次计时，n（或任意其他键）结束程序

    choice = input('是否再次计时？（按 y 重新开始 / 按 n 结束）：')

    if choice.lower() == 'y':
        continue    # 回到循环顶部，开始新一轮计时

    else:
        break       # 退出循环，程序结束

print('已结束计时，再见！')