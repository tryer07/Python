#猜数字游戏

import random
random_num = random.randint(1,100) #随机生成一个1到100的随机数

while True:

    num = int(input('请输入你猜的数字：'))

    if num > random_num:
        print('猜大了')
    elif num < random_num:
        print('猜小了')
    else:
        print('恭喜！猜对了')
        break
print('随机生成的数字是：',random_num)
