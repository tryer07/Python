#导入自定义模块

#import my_function

#使用模块中的功能

# print(my_function.PI)
# print(my_function.NAME)

# my_function.log_separator1()
# my_function.log_separator3()

#注意，如果导入了自定义模块的同时自定义模块中的函数被调用了，它们也会跟着一起输出

#导入自定义模块的功能

# from my_function import PI,NAME,log_separator1,log_separator3
from my_function import *

print(PI)
print(NAME)

log_separator1()
log_separator3()


