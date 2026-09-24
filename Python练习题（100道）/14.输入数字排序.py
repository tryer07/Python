#接收用户输入的三个数字，并按照从小到大的顺序输出

#输入三个数字

a = float(input('请输入第一个数字：'))
b = float(input('请输入第二个数字：'))
c = float(input('请输入第三个数字：'))

#通过条件语句排序

if a > b:
    a, b = b, a
if b > c:
    b, c = c, b
if a > b:
    a, b = b, a

#输出结果

print('排序后的数字为：', a, b, c)




