#while循环结构

#while循环的基本结构
# i = 0
# while i < 10:
#     print('我还要向天再借五百年~')
#     i += 1
# else:
#     print('信用不足，无法借用')

#计算1-100之间偶数的和
# total = 0
# i = 1
# while i < 101:
#     if i % 2 == 0:
#         total = total + i
#     i = i + 1
#     print(f'1-100之间偶数和是：{total}')


#计算1-100的偶数和
total = 0
i = 1
while i < 101:
    if i % 2 == 1:
        total += i
    i +=1
    print(f'1-100之间的奇数和是：{total}')