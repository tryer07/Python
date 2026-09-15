#__all__语句可以控制当用户使用from my_function import *语句时所可以调用的内容
#注意from my_function import *语句默认调用模块所有功能

__all__ = ['PI','NAME','log_separator1','log_separator3']

#常量

PI = 3.1415926535
NAME = '外收内放'

#函数

def log_separator1():
    print('-' * 30)

def log_separator2():
    print('+' * 30)

def log_separator3():
    print('#' * 30)

def log_separator4():
    print('*' * 30)

# log_separator1()
# log_separator2()
# log_separator3()
# log_separator4()

#测试函数


if __name__ == '__main__':
    log_separator1()
    log_separator2()
    log_separator3()
    log_separator4()

#这个代码块 if __name__ == '__main__': 可以用作测试语句，不会在调用了该模块的模块中运行，只会在自定义模块中运行

#__name__:Python中的内置变量，表示当前模块的名字(直接运行模块，__name__的值为‘__main__’)。

#当__name__被导入时，输出的是当前导入模块的名字