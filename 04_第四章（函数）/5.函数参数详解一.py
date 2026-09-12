#位置参数与关键字参数

#定义函数
#
# def reg_stu(name,age,gender,city):
#     print(f'注册成功，姓名：{name}，年龄：{age}，性别：{gender}，城市：{city}')
#     return {'name':name,'age':age,'gender':gender,'city':city}

#传参方式一：位置参数

#调用函数
# stu1 = reg_stu('张三','18','男','北京')
# print(stu1)

#传参方式二：关键字参数

#调用函数
# stu2 = reg_stu(name = '李四',age = '21',gender = '男',city = '上海') #这里乱序传递也是可以的
# print(stu2)

#传参方式三：位置 + 关键字参数(必须保证位置参数在前，关键字参数在后)

#调用函数
# stu3 = reg_stu('王五','19',gender = '男',city = '深圳')
# print(stu3)

#位置参数和关键字参数使用上的综上对比
#位置参数：简洁但可读性差，维护难(参数少且不易混淆时使用)
#关键字参数：可读性强易维护但代码繁琐(参数多且容易混淆时使用)


