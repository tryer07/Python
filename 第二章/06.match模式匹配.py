#match结构
# day = int(input('请输入今天周几：'))
# match day:
#     case 1:
#         print('学习')
#     case 2:
#         print('出差')
#     case 3:
#         print('开会')
#     case 4:
#         print('项目报告')
#     case 5:
#         print('周总结')
#     case 6 | 7:
#         print('周末休息')
#     case _:
#         print('输入错误')

#简易计算器
num1 = float(input('请输入第一个数字：'))
num2 = float(input('请输入第二个数字：'))
oper = input('请选择你需要进行的计算(+ - * /):')
match oper:
    case '+':
        print(f'{num1} + {num2} = {num1 + num2}')
    case '-':
        print(f'{num1} - {num2} = {num1 - num2}')
    case '*':
        print(f'{num1} * {num2} = {num1 * num2}')
    case '/' if num2 !=0:
        print(f'{num1} / {num2} = {num1 / num2}')
    case _:
        print('计算不支持!')
