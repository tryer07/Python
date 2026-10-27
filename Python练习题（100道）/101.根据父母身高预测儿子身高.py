# 根据父母身高预测儿子身高（预测公式：(父 + 母) × 0.54）

def input_height(prompt):

    """
    读取并校验一次身高输入，直到得到合法的正数为止
    :param prompt: 输入提示语
    :return: 合法的身高数值（float）
    """

    result = 0.0
    valid = False

    while not valid:
        text = input(prompt).strip()
        try:
            value = float(text)
        except ValueError:
            print('  [输入无效] 请输入数字，例如 175 或 175.5。')
            continue
        # 身高必须为正数，排除 0 和负数
        if value <= 0:
            print('  [输入无效] 身高必须是大于 0 的数字，请重新输入。')
            continue
        result = value
        valid = True

    return result


a = input_height('请输入父亲的身高：')

b = input_height('请输入母亲的身高：')

c = (a + b) * 0.54

print(f'预测儿子的身高可能是{c:.2f}')
