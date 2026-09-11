#案例尝试3

#将1-20的平方数打印成列表

#版本一
num_list = []

for i in range(1,21):
    num_list.append(i**2)

print(num_list)

#版本二(列表推导式的使用)
num_list1 = [i**1 for i in range(1,21)]
print(num_list1)

#案例尝试4(代码过少合并在案例3的下方)

#提取一个列表中的偶数并计算其平方组成新的列表
num_list2 = [1,4,5,7,8,9,10,22,31,33,34,56,78]
num_list3 = [i**2 for i in num_list2 if i % 2 == 0]
print(num_list3)