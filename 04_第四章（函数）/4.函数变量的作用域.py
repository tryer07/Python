#函数变量的作用域(函数进阶)
#全局变量在函数外部和内部都能生效
#局部变量只能在其定义的所在局部(即函数内部)生效

num = 100 #全局变量

#定义函数

def circle_area(r):
    """
    根据所给的半径计算圆的面积
    :param r: 所给半径的值
    :return: 返回圆的面积
    """
    pi = 3.14 #局部变量
    area = pi * r * r
    global num #使用了global声明后，就可以操作全局变量了
    num = 1000 #经过global声明后，尽管这里的num在函数内部，但此时num的值也是赋值给全局变量
    print('num = ',num)
    return area



#调用函数

a = circle_area(10)
print(a)
print('num = ',num)