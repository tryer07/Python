#输入一行字符，分别统计出其中英文字母、空格、数字和其它字符的个数

#输入一行字符

a = input('请输入一个字符串：')
b = 0
c = 0
d = 0
e = 0
#遍历循环取出字符

for i in a:

    #判断字符是否是英文

    if i.isalpha():

        b = b + 1

    #判断字符是否是空格

    elif i.isspace():

        c = c + 1

    #判断字符是否是数字

    elif i.isdigit():

        d = d + 1

    else:

        e = e + 1

print(f'英文字符数量是{b}')
print(f'空格字符数量是{c}')
print(f'数字字符数量是{d}')
print(f'其他字符数量是{e}')