#编写一个程序，实现简单秒表功能，该程序在用户按下回车键后开始计时，在用户中断程序后停止计时。

#导入time模块，用于处理时间相关的任务

import time

#打印提示信息

print("按回车键开始计时，中断程序则停止计时")

#等待用户按下回车键

input('准备...')

#定义变量保存计时开始时间

start_time = time.time()

#打印消息表明计时开始

print("计时开始...")

#让程序进入一个无限循环，等待用户中断程序

try:
    while True:
        # 计算经过的时间

        elapsed_time = time.time() - start_time

        # 打印经过的时间

        print(f'\r经过的时间为：{elapsed_time:.2f}秒', end='')  # 这里是一个格式限制，end = '\r' 表示不换行，光标返回行首

        # 让程序暂停一秒以每秒更新一次显示

        time.sleep(1)

except KeyboardInterrupt:

    end_time = time.time()

    #计算总时间

    total_time = round(end_time - start_time,2)

    print(f'\n总时间为：{total_time:.2f}秒', end='')
