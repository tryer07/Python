#定义一个函数，该函数用于计算并返回用户输入的半径的圆的面积(结果保留两位小数)

#引入math模块

import math

#用户输入圆的半径

r = int(input('请输入圆的半径：'))

def circle_area(r):
    """
    根据所给的半径计算圆的面积
    :param r: 圆的半径的值
    :return: 返回圆的面积
    """

    area = math.pi * r * r

    area = round(area, 2)

    return area

#调用函数

print('圆的面积为：', circle_area(r))
