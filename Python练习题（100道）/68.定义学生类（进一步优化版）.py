# 定义一个学生类，用于存储学生基本信息(如姓名、年龄、学号)，并提供查询这些信息的方法
# 进一步优化版：支持连续录入多个学生 + 用户选择继续/退出 + 退出时汇总展示所有学生信息


# ---------- 学生类 ----------
class Student:

    """存储学生基本信息，并提供查询方法"""

    # 初始化学生对象
    def __init__(self, name, age, sid):
        self.name = name  # 学生姓名
        self.age = age    # 学生年龄
        self.sid = sid    # 学生学号

    def get_name(self):
        """
        获取学生姓名
        :return: 学生姓名
        """
        return self.name

    def get_age(self):
        """
        获取学生年龄
        :return: 学生年龄
        """
        return self.age

    def get_sid(self):
        """
        获取学生学号
        :return: 学生学号
        """
        return self.sid

    def info(self):
        """
        以美观的格式汇总输出单个学生信息
        :return: 格式化后的字符串
        """
        line = '-' * 30
        return (
            f'{line}\n'
            f'  姓    名：{self.name}\n'
            f'  年    龄：{self.age} 岁\n'
            f'  学    号：{self.sid}\n'
            f'{line}'
        )


# ---------- 输入辅助函数 ----------
def input_name():
    """输入姓名：不能为空"""
    while True:
        name = input('  请输入学生姓名：').strip()
        if name:
            return name
        print('  [输入无效] 姓名不能为空，请重新输入。')


def input_age():
    """输入年龄：必须是整数，且在 0 ~ 150 之间"""
    while True:
        raw = input('  请输入学生年龄(0-150 的整数)：').strip()
        try:
            age = int(raw)
        except ValueError:
            print('  [输入无效] 年龄必须是整数，请不要输入字母或符号。')
            continue

        # 范围校验放在 try/except 之外；边界用 or
        if age < 0 or age > 150:
            print('  [输入无效] 年龄超出合理范围(0-150)，请重新输入。')
            continue

        return age


def input_sid(existing_students):
    """输入学号：不能为空，且不能与已录入学生重复"""
    while True:
        sid = input('  请输入学生学号：').strip()
        if not sid:
            print('  [输入无效] 学号不能为空，请重新输入。')
            continue

        # 学号去重：遍历已有学生，检查是否冲突
        for s in existing_students:
            if s.get_sid() == sid:
                print(f'  [输入无效] 学号 {sid} 已被 "{s.get_name()}" 使用，请换一个。')
                break
        else:
            return sid


def input_yes_no(prompt):
    """
    询问 y/n 问题，返回 True/False
    支持 y / Y / 是 / n / N / 否
    """
    while True:
        ans = input(prompt).strip().lower()
        if ans in ('y', 'yes', '是'):
            return True
        if ans in ('n', 'no', '否'):
            return False
        print('  [输入无效] 请输入 y(继续) 或 n(退出)。')


def collect_one_student(students):
    """录入一个学生的完整信息，并加入 students 列表"""
    print('\n------------------ 录入第 {} 位学生 ------------------'.format(len(students) + 1))
    name = input_name()
    age = input_age()
    sid = input_sid(students)
    students.append(Student(name, age, sid))
    print('  ✔ 已录入：{} / {} 岁 / 学号 {}'.format(name, age, sid))


def show_all_students(students):
    """退出时统一展示所有学生信息"""
    print('\n')
    print('=' * 40)
    print(f'              学生信息汇总 (共 {len(students)} 人)')
    print('=' * 40)

    if not students:
        print('  本次未录入任何学生信息。')
        print('=' * 40)
        return

    for idx, student in enumerate(students, start=1):
        print(f'\n【No.{idx}】')
        print(student.info())

    print('\n' + '=' * 40)
    print(f'  全部录入完成，共 {len(students)} 位学生。')
    print('=' * 40)


# ---------- 主程序 ----------
if __name__ == '__main__':
    print('==== 欢迎使用学生信息录入系统（多学生版）====')
    print('请按照提示依次输入学生信息；每录入一位，可选择继续或退出。')

    students = []  # 用于累积所有已录入的学生对象

    # 外层主循环：不断询问"要不要录下一位"
    while True:
        collect_one_student(students)

        # 询问是否继续
        if not input_yes_no('\n是否继续录入下一位学生？(y=继续 / n=退出并查看汇总)：'):
            break

    # 退出循环后，展示全部信息
    show_all_students(students)