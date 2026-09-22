#打印一个99乘法表
from click.globals import push_context

#打印行数

for i in range(1,10):

    #打印列数

    for j in range(1,i + 1):

        #打印乘法表

        print(f'{j} * {i} = {i * j}',end = '\t')

        #换行

    print(end = '\n')