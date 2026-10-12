# 实现一个简单的学生成绩管理系统，支持添加学生、记录学生成绩，并计算每个学生成绩的平均值
# 实现的内容：
# 1. 修复原版 Student.calculate_average 引用不存在的 self.students 导致的 AttributeError，平均分改由学生自身负责计算
# 2. StudentGradeManager 统一存储 Student 对象（而不是裸列表），让学生类与管理类正确协作
# 3. 菜单式交互：添加学生 / 记录成绩 / 查看平均分 / 查看全部 / 退出
# 4. 成绩输入统一校验（必须是 0-100 的数字），输错不会崩溃，而是重新提示（标志位循环 + 循环外统一返回）
# 5. 属性与方法补充类型注解，且 calculate_average 恒返回 float（不再携带 None），
#    平均分查询改由 show_average 在校验通过后才格式化输出，从结构上消除 PyCharm 的类型格式化警告


# ---------- 学生类 ----------
class Student:

    """用于表示一个学生及其成绩列表"""

    def __init__(self, name):
        """
        初始化学生对象
        :param name: 学生姓名
        """
        self.name = name                      # 学生姓名
        self.grades: list[float] = []         # 学生成绩列表，初始为空（显式注解，避免推断成 list[Any]）

    def add_grade(self, grade):
        """
        添加一条学生成绩
        :param grade: 成绩（数字）
        """
        self.grades.append(grade)

    def calculate_average(self):
        """
        计算该学生成绩的平均值
        :return: 成绩平均值（恒为 float）；尚无成绩时返回 0.0，由调用方通过 grades 是否为空区分
        """
        if not self.grades:
            return 0.0
        return sum(self.grades) / len(self.grades)

    def info(self):
        """
        汇总该学生的成绩信息
        :return: 格式化后的字符串
        """
        if not self.grades:
            return f'  {self.name}：尚未记录任何成绩'
        # calculate_average 已保证返回 float，格式化处不会再混入 None
        average = self.calculate_average()
        return (
            f'  {self.name}：共 {len(self.grades)} 条成绩 '
            f'{self.grades}，平均分 {average:.2f}'
        )


# ---------- 学生成绩管理类 ----------
class StudentGradeManager:

    """学生成绩管理类，负责学生的增删查与成绩维护"""

    def __init__(self):
        """初始化学生成绩管理对象"""
        # 存储学生信息的字典，键为学生姓名，值为 Student 对象（显式注解，消除取值被推断为 Any 的问题）
        self.students: dict[str, Student] = {}

    def add_student(self, name):
        """
        添加学生信息
        :param name: 要添加的学生姓名
        :return: 添加成功返回 True，已存在返回 False
        """
        if name in self.students:
            print(f'  学生 {name} 已经存在，无需重复添加。')
            return False
        self.students[name] = Student(name)
        print(f'  学生 {name} 添加成功。')
        return True

    def add_grade(self, name, grade):
        """
        为指定学生添加一条成绩
        :param name: 学生姓名
        :param grade: 成绩（数字）
        :return: 添加成功返回 True，学生不存在返回 False
        """
        if name not in self.students:
            print(f'  查无此人：{name}，请先添加该学生。')
            return False
        self.students[name].add_grade(grade)
        print(f'  已为 {name} 记录成绩 {grade}。')
        return True

    def show_average(self, name):
        """
        查询并打印指定学生的平均成绩，内部完成“学生是否存在 / 是否已有成绩”的校验
        :param name: 学生姓名
        :return: 成功打印返回 True，学生不存在或无成绩返回 False
        """
        if name not in self.students:
            print(f'  查无此人：{name}，请先添加该学生。')
            return False

        student = self.students[name]
        if not student.grades:
            print(f'  {name} 尚未记录任何成绩，无法计算平均分。')
            return False

        # 走到这里必有成绩，calculate_average 恒为 float，不存在 None 参与格式化的可能
        average = student.calculate_average()
        print(f'  {name} 的平均分为：{average:.2f}')
        return True

    def show_all(self):
        """展示所有学生的成绩与平均分"""
        print('\n' + '=' * 40)
        print(f'              学生成绩汇总 (共 {len(self.students)} 人)')
        print('=' * 40)

        if not self.students:
            print('  系统中还没有任何学生。')
        else:
            for student in self.students.values():
                print(student.info())

        print('=' * 40)


# ---------- 输入辅助函数 ----------
def input_name(prompt):
    """
    输入姓名：不能为空（标志位循环 + 循环外统一返回）
    :param prompt: 提示文字
    :return: 去除首尾空格后的姓名
    """
    # 初始化结果变量与标志位，保证循环外有明确类型的唯一返回值
    name = ''
    valid = False

    while not valid:
        raw = input(prompt).strip()
        if not raw:
            print('  [输入无效] 姓名不能为空，请重新输入。')
            continue
        # 成功时更新结果并置标志位，让循环自然退出
        name = raw
        valid = True

    return name


def input_grade(prompt):
    """
    输入成绩：必须是 0-100 之间的数字（标志位循环 + 循环外统一返回）
    :param prompt: 提示文字
    :return: 合法成绩（浮点数）
    """
    grade = 0.0
    valid = False

    while not valid:
        try:
            value = float(input(prompt))
        except ValueError:
            print('  [输入无效] 成绩必须是数字，请不要输入字母或符号。')
            continue

        # 范围校验放在 try/except 之外，用独立 if 判断
        if value < 0 or value > 100:
            print('  [输入无效] 成绩超出合理范围(0-100)，请重新输入。')
            continue

        grade = value
        valid = True

    return grade


# ---------- 主程序 ----------
if __name__ == '__main__':

    print('==== 欢迎使用简单版学生成绩管理系统 ====')

    manager = StudentGradeManager()

    # 菜单主循环：用户可反复选择操作，直到选择退出
    while True:

        print('\n请选择要执行的操作：')
        print('1. 添加学生')
        print('2. 为学生记录成绩')
        print('3. 查询学生平均分')
        print('4. 查看所有学生成绩')
        print('0. 退出系统')

        choice = input('请输入您的选择（0 / 1 / 2 / 3 / 4）：').strip()

        if choice == '1':
            name = input_name('  请输入要添加的学生姓名：')
            manager.add_student(name)
        elif choice == '2':
            name = input_name('  请输入要记录成绩的学生姓名：')
            grade = input_grade('  请输入该学生的成绩(0-100)：')
            manager.add_grade(name, grade)
        elif choice == '3':
            name = input_name('  请输入要查询平均分的学生姓名：')
            # 存在性/成绩校验与格式化输出都交给 show_average，主流程不再接触可能含 None 的返回值
            manager.show_average(name)
        elif choice == '4':
            manager.show_all()
        elif choice == '0':
            print('已退出系统，感谢使用，再见！')
            break
        else:
            print('  无效的选项，请输入 0、1、2、3 或 4。')
