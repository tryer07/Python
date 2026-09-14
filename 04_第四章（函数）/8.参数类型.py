#函数参数类型

#加

def add(x,y):
    return x + y

#减

def subtract(x,y):
    return x - y

#乘

def multiply(x,y):
    return x * y

#除

def divide(x,y):
    return x / y

#计算

def calculate(x,y,oper):
    return oper(x,y)
#注意这里的oper需要传递的是函数，不能传递其它例如整数一类的东西

print(calculate(10, 20, add))