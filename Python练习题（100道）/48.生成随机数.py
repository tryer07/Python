#编写一个程序，使用random模块来生成各种随机数

#导入random模块

import random

#生成一个介于0和1(不包含1)之间的随机浮点数

random_number1 = random.random()

print(random_number1)

#生成指定范围内的随机整数(闭区间，两边都包含)

random_number2 = random.randint(10,100)

print(random_number2)

#从给定序列中随机选择一个元素

list1 = [1,2,3,4,5,6]

random_element1 = random.choice(list1)

print(random_element1)

#给定序列中的元素随机排序(只能是列表)

list2 = [1,3,5,7,9]

random.shuffle(list2)

print(list2)