#函数的定义
#函数定义的时候并不会运行，只有调用后才会运行
#且函数必须先定义再调用

# def out_line():
#     print('-----')
#     print(' ---')
#     print('  -  ')

# def out_line1():
#     print('  -  ')
#     print(' ---')
#     print('-----')
# #函数调用
# out_line()
# out_line1()

#函数的参数与返回值
#1.计算圆的面积

def circle_area(r):
    """
    根据所给的半径计算圆的面积
    :param r: 圆的半径的值
    :return:返回圆的面积
    """
    area = 3.14 * r * r
    return area

a = circle_area(5)
print(a)

#2.计算长方形的面积

def rectangle_area(l,w):
    """
    根据所给的长和宽计算长方形的面积
    :param l: 长方形的长
    :param w: 长方形的宽
    :return: 返回长方形的面积
    """
    area = l * w
    return area

b = rectangle_area(10,5)
print(b)

#这是一个调用语句，可以看到具体函数的说明文档

help(rectangle_area)

#3.计算圆的面积和周长

def circle_area_length(r):
    """
    根据圆的半径计算圆的面积和周长
    :param r:圆的半径的值
    :return:返回圆的面积和周长
    """
    area = round(3.14 * r * r,1)
    length = round(2 * 3.14 * r,1)
    #Python内置语句，round语句结构:round(number,n * digits),其中digits即为保留几位小数点
    return area,length

c = circle_area_length(10)
print(c)
print(type(c))

d,e = circle_area_length(5)
print(d)
print(e)
print(type(d))
print(type(e))

#函数的嵌套调用(遵循栈结构)

def function_a():
    print('a--before')
    function_b()
    print('a--after')

def function_b():
    print('b--before')
    function_c()
    print('b--after')

def function_c():
    print('c')

function_a()
print('函数已调用完毕')
