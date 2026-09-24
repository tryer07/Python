#给定一个已排序好的整数列表，插入一个数，并根据原整数列表的排序顺序插入

#定义一个已排序的整数列表(这里以从小到大的顺序排列)

li = [11,23,31,47,59]

#让用户输入一个数字

num = int(input('请输入一个数：'))

#遍历列表，寻找要插入的位置

for i in range(len(li)):

    # 如果len(li)大于要插入的数，说明找到了插入位置

    if li[i] > num:

        # 在位置i插入num

        li.insert(i,num)

        break

#如果循环没有通过break结束，则num比所有数都大，将num放在列表末尾

else:
    li.insert(num,num)

print(li)





