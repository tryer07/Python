num = int(input('请输入你要计算的数字：'))

result = 1

for i in range(1,num + 1):

    result *= i

print(f'这个数的阶乘结果是{result}')