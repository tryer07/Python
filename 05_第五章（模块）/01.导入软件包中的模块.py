#导入模块

# import utils.my_function

# utils.my_function.log_separator1()
# utils.my_function.log_separator2()
# utils.my_function.log_separator3()
# utils.my_function.log_separator4()

# from utils import my_function

# my_function.log_separator1()
# my_function.log_separator2()
# my_function.log_separator3()
# my_function.log_separator4()

#注意，要写from utils import * 必须在__init__这个模块中输入__all__ = ['my_function','my_varchar']这样的语句，否则默认不调用

from utils import *

my_function.log_separator1()
my_function.log_separator2()
my_function.log_separator3()
my_function.log_separator4()

print(my_varchar.PI)
print(my_varchar.NAME)

#导入模块中的具体功能

from utils.my_function import log_separator1,log_separator3

log_separator1()
log_separator3()