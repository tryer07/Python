#解包与组包的相关介绍

# t1 = (5,7,9,1)
# t2 = (5,7,9,1)

# #基础解包
# a,b,c,d = t1
# print(a,b,c,d)

# #扩展解包
# #思路一:
# x,*y,z = t2
# print(x,y,z)

# #思路二
# s,*o = t2
# print(s,o)

# #思路三
# *o,e = t2
# print(o,e)

#解包与组包的进一步讲解
t1 = (1,3,5,7,9,2,4,6,8,10)
t2 = 1,3,5,7,9,2,4,6,8,10
print(t1)
print(t2)

#'*'解包的使用

#要求：截取第一个，第二个和最后一个元素，其他不要

first,second,*other1,last = t1
print(first,second,last)
first,second,*other2,last = t2
print(first,second,last)