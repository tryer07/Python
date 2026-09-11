#猜数字游戏改进
import random

while True:  # 外层循环：控制是否开始新一局
    random_num = random.randint(1, 100)  # 每局重新生成随机数
    print('新一局开始！我已经想好了一个1到100之间的数字。')

    while True:  # 内层循环：猜数字
        try:
            num = int(input('请输入你猜的数字：'))
        except ValueError:
            print('请输入有效的整数！')
            continue

        if num > random_num:
            print('猜大了')
        elif num < random_num:
            print('猜小了')
        else:
            print('恭喜！猜对了')
            break

    # 询问是否继续
    while True:  # 这个循环用于确保玩家输入有效的选项
        choice = input('是否再玩一次？(y/n)：').strip().lower()
        if choice in ['y', 'yes']:
            break  # 跳出询问循环，继续外层循环（开始新一局）
        elif choice in ['n', 'no']:
            print('感谢游玩，再见！')
            exit()  # 或者 break 两次，但 exit() 直接结束程序更简单
        else:
            print('请输入 y 或 n。')