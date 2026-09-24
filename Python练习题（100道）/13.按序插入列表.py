#给定一个列表，将用户输入的数字按照原定列表顺序插入列表中

li = [11, 23, 31, 47, 59]
num = int(input('请输入一个数：'))

# 遍历列表，寻找第一个比 num 大的数的位置

for i in range(len(li)):
    if li[i] > num:

        # 找到了，把 num 插入到这个位置（原来的元素向右移动）

        li.insert(i, num)
        break
else:
    # 循环没有被 break，说明 num 比列表里所有数都大
    # 直接追加到列表末尾

    li.append(num)

print(li)



