# 从 student_grade_file 文件中读取学生数据(学号、姓名及语数英三科成绩)，并根据总成绩进行排序
# 实现的内容：
# 1. read_file 跳过表头与空行，把每一行解析为 [学号, 姓名, 语文, 数学, 英语]，成绩转为 int
# 2. sort_data 按语数英三科"总分"从高到低排序
# 3. write_file 把排序结果连同总分写入新文件，读写均指定 utf-8 编码，避免中文乱码
# 4. 借助脚本自身所在目录拼接路径，保证从项目根运行也能正确找到数据文件
# 5. 增加主程序入口，读取 -> 排序 -> 终端打印排行榜 -> 写入文件

import os


def read_file(file_name):

    """
    读取文件内容，跳过表头与空行，逐行解析
    :param file_name: 数据文件名
    :return: 学生数据列表，每个元素为 [学号, 姓名, 语文, 数学, 英语]，其中三科成绩为 int
    """

    students = []

    with open(file_name, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for line in lines:
        # 去除首尾空白（含换行符）
        line = line.strip()
        # 跳过空行
        if not line:
            continue
        fields = line.split(',')
        # 跳过表头行：第一个字段不是纯数字即视为表头
        if not fields[0].isdigit():
            continue
        student_id = fields[0]
        name = fields[1]
        chinese = int(fields[2])
        math = int(fields[3])
        english = int(fields[4])
        students.append([student_id, name, chinese, math, english])

    return students


def sort_data(data):

    """
    根据语数英三科总成绩从高到低排序
    :param data: 学生数据列表，每个元素为 [学号, 姓名, 语文, 数学, 英语]
    :return: 排序后的数据列表
    """

    return sorted(data, key=lambda x: x[2] + x[3] + x[4], reverse=True)


def write_file(file_name, data):

    """
    将排序后的数据写入文件，每行附带三科总分
    :param file_name: 输出文件名
    :param data: 排序后的学生数据列表
    :return: None
    """

    with open(file_name, 'w', encoding='utf-8') as file:
        file.write('学号,姓名,语文,数学,英语,总分\n')
        for student in data:
            total = student[2] + student[3] + student[4]
            file.write(
                f'{student[0]},{student[1]},'
                f'{student[2]},{student[3]},{student[4]},{total}\n'
            )


if __name__ == '__main__':

    # 以脚本自身所在目录为基准拼接路径，避免因工作目录不同而找不到文件
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, 'student_grade_file.txt')
    output_path = os.path.join(base_dir, 'student_grade_sorted.txt')

    # 1. 读取数据
    students = read_file(input_path)
    if not students:
        print('未能从文件中读取到任何学生数据，请检查文件内容与路径。')
    else:
        print(f'成功读取 {len(students)} 名学生的数据。')

        # 2. 按总分排序
        ranked = sort_data(students)

        # 3. 终端打印排行榜
        print('\n' + '=' * 52)
        print('              学生成绩排行榜（按语数英总分降序）')
        print('=' * 52)
        print(f'{"排名":<4}{"学号":<8}{"姓名":<8}{"语文":>5}{"数学":>5}{"英语":>5}{"总分":>7}')
        print('-' * 52)
        for rank, student in enumerate(ranked, start=1):
            total = student[2] + student[3] + student[4]
            print(
                f'{rank:<4}{student[0]:<8}{student[1]:<8}'
                f'{student[2]:>5}{student[3]:>5}{student[4]:>5}{total:>7}'
            )
        print('=' * 52)

        # 4. 写入排序后的文件
        write_file(output_path, ranked)
        print(f'\n排序结果已写入文件：{output_path}')
