#有四个数字1,2,3,4，统计它们可以组成多少个不同且无重复数字的三位数

#定义计数器

count = 0

#嵌套循环遍历所有可能的三位数

for i in range(1,5):
    for j in range(1,5):
        for k in range(1,5):

            #判断数字是否重复

            if i != j and j != k and i !=k:
                print(i, j, k)
                count += 1

#打印结果

print('一共有', count, '个不同且无重复数字的三位数')
