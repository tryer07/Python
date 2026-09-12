#默认参数

#定义函数
def reg_stu(name = '张三',age = '18',gender = '男',city = '上海'):
    print(f'注册成功，姓名：{name}，年龄：{age}，性别：{gender}，城市：{city}')
    return {'name':name,'age':age,'gender':gender,'city':city}

#调用函数

stu1 =  reg_stu()
print(stu1)