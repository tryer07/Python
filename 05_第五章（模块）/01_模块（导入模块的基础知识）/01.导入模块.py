#1.导入模块--->调用方式：模块名.功能名

#import random

# import random as rd #将random改名成rd

# for i in range(10):
#     print(rd.randint(1,100)) #这里1-100是闭区间

#2.导入模块中的功能--->from ... import ....

# from random import randint

# from random import randint as rint #将randint改名成rint

from random import *

for i in range(10):
    print(randint(1,100))
