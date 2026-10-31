# 素数：在大于1的自然数中，除了1和这个数本身没有其它因数的自然数。

#方法一：

print('这是一个判断输入数字是否为素数的程序')

num = int(input('请输入你需要判断的数字：'))

if num <= 1:
    print(f'{num}不是素数')
else:
    for i in range(2, num):
        if num % i == 0:
            print(f'{num}不是素数')
            break
    else:
        # 注意这个 else 是和 for 对齐的！
        # 只有当循环完整跑完，没有被 break 打断时，才会执行这里
        print(f'{num}是素数')

#方法二；

num = int(input('请输入你需要判断的数字：'))

if num <= 1:
    print(f'{num}不是素数')
else:
    for i in range(2, num):
        if num % i == 0:
            print(f'{num}不是素数')
            break
    else:
        print(f'{num}是素数')