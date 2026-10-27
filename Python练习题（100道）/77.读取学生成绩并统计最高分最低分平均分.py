# 从 student_grade_file 文件中读取学生成绩数据，统计最高分、最低分和平均分（保留两位小数）
# 实现的内容：
# 1. 定义函数统计_file：文件名为固定值无需参数，返回值用元组 (最高分, 最低分, 平均分) 封装三个统计结果
# 2. with open 以 utf-8 编码打开文件，readlines() 获取行列表，切片/strip 去除末尾换行符，避免中文乱码
# 3. 遍历每一行，split(',') 按逗号分割，提取成绩转为 float 后存入列表
#    （容器选择：成绩可变且允许重复，列表最合适；分数可能带小数，故用 float 而非 int）
# 4. 内置函数统计：max() 求最高分，min() 求最低分，round(sum() / len(), 2) 求平均分
# 5. 调用函数后用元组解包接收结果，f-string 格式化打印

import os


def statistics_file():

    """
    从成绩文件中读取所有分数，统计最高分、最低分和平均分
    （文件名固定，故函数无需参数；结果以元组返回，体现模块化封装思想）
    :return: 元组 (最高分, 最低分, 平均分)，平均分保留两位小数
    """

    grades = []

    # 以脚本自身所在目录为基准拼接路径，保证从项目根运行也能正确找到数据文件
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'student_grade_file.txt')

    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for line in lines:
        # 切片去除末尾换行符，再 strip 清理首尾空白
        line = line.strip()
        # 跳过空行
        if not line:
            continue
        fields = line.split(',')
        # 跳过表头行：第一个字段不是纯数字即视为表头
        if not fields[0].isdigit():
            continue
        # 成绩可能是带小数点的数值，转为 float 兼容整数和小数
        grades.append(float(fields[-1]))

    # 用内置函数统计：max 最高分、min 最低分、sum/len 平均分（round 保留两位小数）
    return max(grades), min(grades), round(sum(grades) / len(grades), 2)


if __name__ == '__main__':

    # 元组解包，分别接收三个统计结果
    highest, lowest, average = statistics_file()

    # f-string 格式化输出
    print(f'最高分为：{highest}')
    print(f'最低分为：{lowest}')
    print(f'平均分为：{average}')
