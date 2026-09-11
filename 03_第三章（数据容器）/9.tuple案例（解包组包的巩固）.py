#利用解包与组包完成数据交换

#案例1

# a = 10
# b = 20
# 组包
# t = b,a
# 解包
# a,b = t
# 完成交换并输出
# print(a)
# print(b)

#案例2
a = 100
b = 200
c = 300
#组包
t = c,b,a
#解包
a,b,c = t
#完成交换并输出
print(a)
print(b)
print(c)