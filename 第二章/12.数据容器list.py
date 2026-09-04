#list容器(数据支持修改)

#list的定义
s = [1,2,3,4,'abc',6,7,8,9]
print(type(s))

#获取
print(s[0])  #正向索引
print(s[-9]) #反向索引

#修改
s[4] = 'ABC'
print(s[4])
print(s)

#删除
del s[4]
print(s)

#遍历
for i in s:
    print(i)

#切片操作
s1 = ['A','B','C','D','E','F']
print(s1[0:3:1])
print(type(s1[0:3:1]))
print(s1[:3:])

#常用方法

#append：末端插入
s2 = [188, 288, 388, 488, 588, 688, 788, 888]
s2.append(8888)
print(s2)

#insert：制定插入
s2.insert(1,88)
print(s2)

#remove：移除第一个匹配到的元素
s2.remove(s2[0])
print(s2)

#pop：删除指定元素并返回
e = s2.pop()
print(e)

#sort：排序
s3 = [188,888,288,388,588,688,788,488]
s3.sort()
print(s3)

#reverse：反转
s3.reverse()
print(s3)