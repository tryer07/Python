#给定一个字典，姓名作为键，年龄作为值，找出年龄最大者的姓名和年龄，并打印出来。

#定义对应字典

people = {'张三':18,'李四':50,'王五':29,'赵六':22}

#定义变量接收最大年龄和对应姓名

max_age = float('-inf') #这里的'-inf'表示负无穷大
max_name = ''           #将姓名初始化成空字符

#遍历字典中的键值对

for name,age in people.items():

    #如果当前年龄大于已知的最大年龄

    if age > max_age:

    #更新最大年龄以及其对应的姓名

        max_age = age
        max_name = name

#打印结果

print(f'年龄最大者的姓名：',max_name)
print(f'年龄最大者的年龄：',max_age)




