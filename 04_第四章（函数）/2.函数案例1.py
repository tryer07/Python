#案例1：定义一个函数，根据传入的底和高计算三角形的面积((底 * 高) / 2)

def triangle_area(b,h):
    """
    根据传入的底和高计算三角形的面积
    :param b: 三角形的底
    :param h: 三角形的高
    :return: 返回三角形的面积
    """
    area = (b * h) / 2
    return area
a = triangle_area(10,20)
print(a)

#案例2：定义一个函数，计算传入字符串的元音字母的个数(元音字母：aeiou / AEIOU)

def count_aeiouAEIOU(s):
    """
    统计传入的字符串中元音字母的个数
    :param s: 字符串
    :return:  返回元音字母的个数
    """
    num = 0
    for i in s:
        if i in 'aeiouAEIOU':
            num += 1
    return num

print(count_aeiouAEIOU('Hello World Hello Python'))



