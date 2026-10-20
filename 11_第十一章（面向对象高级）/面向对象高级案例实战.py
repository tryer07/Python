# ============================================================
# 案例名称：《书海灯塔 · 命令行图书借阅系统》
# 面向对象高级章综合实战：
#   封装   —— Member 私有卡号/密码/姓名，对外只给查询与校验接口
#   继承   —— NormalMember / VIPMember 继承 Member，借阅上限各自重写
#   多态   —— 系统只调 member.get_max_borrow()，普通/VIP 自动返回不同上限
#   持久化 —— members.json / books.json 保存会员与图书数据（首次运行自动生成示例数据）
# 业务规则：
#   普通会员最多借 3 本；VIP会员最多借 6 + VIP等级（等级未指定默认为 1）
#   库存可用数量 > 0 才能借阅；借出可用数 -1，归还可用数 +1
# ============================================================
import json
import pathlib

# 数据文件与本 py 放同一目录，用 __file__ 定位，不依赖运行时工作目录
_DATA_DIR = pathlib.Path(__file__).parent

# 首次运行时写入的示例图书数据（编号、标题、作者、总数量、可用数量）
_DEFAULT_BOOKS: list[dict] = [
    {"book_id": "B001", "title": "三体", "author": "刘慈欣", "total": 5, "available": 5},
    {"book_id": "B002", "title": "平凡的世界", "author": "路遥", "total": 3, "available": 3},
    {"book_id": "B003", "title": "战争与和平", "author": "托尔斯泰", "total": 2, "available": 2},
    {"book_id": "B004", "title": "我是猫", "author": "夏目漱石", "total": 1, "available": 1},
    {"book_id": "B005", "title": "唐诗三百首（绝版典藏）", "author": "佚名", "total": 2, "available": 0},
]

# 首次运行时写入的示例会员数据（type 区分普通会员 / VIP会员，密码仅供学习演示）
_DEFAULT_MEMBERS: list[dict] = [
    {"type": "normal", "card_no": "1001", "password": "123", "name": "张三"},
    {"type": "normal", "card_no": "1002", "password": "123", "name": "李四"},
    {"type": "vip", "card_no": "9001", "password": "vip888", "name": "王五", "vip_level": 2},
    # vip_level 不指定时，VIPMember 默认按等级 1 处理
    {"type": "vip", "card_no": "9002", "password": "456", "name": "赵六"},
]


# ------------------------------------------------------------
# Book 图书类：封装图书信息与借还书的库存逻辑
# ------------------------------------------------------------
class Book:
    # 参数与数值属性都显式标注 int/str：避免无注解参数经 min() 推导出
    # SupportsDunderLT/GT 联合类型，导致布尔/整数返回处报类型不符
    def __init__(self, book_id: str, title: str, author: str, total: int, available: int):
        self.book_id = book_id
        self.title = title
        self.author = author
        self.total: int = total
        # 可用数量不得大于总数量
        self.available: int = min(available, total)

    # 是否还有剩余库存可供借阅
    def is_available(self) -> bool:
        return self.available > 0

    # 每借出一本，可用数量减 1
    def borrow(self) -> None:
        self.available -= 1

    # 每归还一本，可用数量加 1（并以总数量为上限保护）
    def return_back(self) -> None:
        self.available = min(self.available + 1, self.total)

    # 序列化为写回 JSON 的字典
    def to_dict(self) -> dict:
        return {
            "book_id": self.book_id,
            "title": self.title,
            "author": self.author,
            "total": self.total,
            "available": self.available,
        }


# ------------------------------------------------------------
# Member 会员父类：封装卡号、密码、姓名等通用会员属性（私有化演示）
# ------------------------------------------------------------
class Member:
    # 借阅记录存 Book 对象引用，公共属性便于系统层读写
    def __init__(self, card_no: str, password: str, name: str):
        self.__card_no: str = card_no
        self.__password: str = password
        self.__name: str = name
        self.borrowed_books: list[Book] = []

    # 私有属性对外只读：提供查询接口，不提供修改入口
    def get_card_no(self) -> str:
        return self.__card_no

    def get_name(self) -> str:
        return self.__name

    # 密码不直接返回，只回答"校验是否通过"
    def check_password(self, password: str) -> bool:
        return password == self.__password

    # 最大可借数量：父类不定义具体规则，由子类重写（多态的"接口语义"）
    def get_max_borrow(self) -> int:
        return 0

    # 是否已达到借阅上限
    def is_borrow_full(self) -> bool:
        return len(self.borrowed_books) >= self.get_max_borrow()

    # 序列化：子类通过 super().to_dict() 复用公共字段
    def to_dict(self) -> dict:
        return {
            "type": "normal",
            "card_no": self.__card_no,
            "password": self.__password,
            "name": self.__name,
            "borrowed_ids": [book.book_id for book in self.borrowed_books],
        }


# ------------------------------------------------------------
# NormalMember 普通会员：重写借阅上限为固定 3 本
# ------------------------------------------------------------
class NormalMember(Member):
    def get_max_borrow(self) -> int:
        return 3


# ------------------------------------------------------------
# VIPMember VIP会员：重写借阅上限为 6 + VIP等级，等级默认 1
# ------------------------------------------------------------
class VIPMember(Member):
    def __init__(self, card_no: str, password: str, name: str, vip_level: int = 1):
        super().__init__(card_no, password, name)
        self.__vip_level: int = vip_level

    def get_vip_level(self) -> int:
        return self.__vip_level

    def get_max_borrow(self) -> int:
        return 6 + self.__vip_level

    # 在父类公共字段基础上，补充 VIP 专属字段
    def to_dict(self) -> dict:
        data = super().to_dict()
        data["type"] = "vip"
        data["vip_level"] = self.__vip_level
        return data


# ------------------------------------------------------------
# LibrarySystem 图书管理系统：登录、菜单、借书、还书、查看借阅、退出
# ------------------------------------------------------------
class LibrarySystem:
    def __init__(self):
        # 编号 -> 对象 的索引，O(1) 查找
        self.books: dict[str, Book] = {}
        self.members: dict[str, Member] = {}

    # 数据文件读写：不存在则先写入示例数据
    @staticmethod
    def _path(file_name: str) -> pathlib.Path:
        return _DATA_DIR / file_name

    def _ensure_data_file(self, file_name: str, default_data: list) -> None:
        file_path = self._path(file_name)
        if not file_path.exists():
            file_path.write_text(json.dumps(default_data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read_json(self, file_name: str) -> list:
        content = self._path(file_name).read_text(encoding="utf-8")
        return json.loads(content)

    # 启动时加载图书与会员数据，并恢复会员的在借记录
    def load_data(self) -> None:
        self._ensure_data_file("books.json", _DEFAULT_BOOKS)
        self._ensure_data_file("members.json", _DEFAULT_MEMBERS)

        for item in self._read_json("books.json"):
            book = Book(item["book_id"], item["title"], item["author"], item["total"], item["available"])
            self.books[book.book_id] = book

        for item in self._read_json("members.json"):
            if item["type"] == "vip":
                member: Member = VIPMember(item["card_no"], item["password"], item["name"], item.get("vip_level", 1))
            else:
                member = NormalMember(item["card_no"], item["password"], item["name"])
            # 在借记录按图书编号还原为 Book 对象引用
            for book_id in item.get("borrowed_ids", []):
                if book_id in self.books:
                    member.borrowed_books.append(self.books[book_id])
            self.members[member.get_card_no()] = member

    # 借还发生后立即写回 JSON，保证库存与借阅记录不丢失
    def save_data(self) -> None:
        books_data = [book.to_dict() for book in self.books.values()]
        members_data = [member.to_dict() for member in self.members.values()]
        self._path("books.json").write_text(json.dumps(books_data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._path("members.json").write_text(json.dumps(members_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 会员登录：卡号密码都正确才放行；输 0 退出程序
    def login(self) -> Member | None:
        print("\n【会员登录】未登录不能进入系统功能")
        while True:
            card_no = input("请输入会员卡号（输0退出系统）：").strip()
            if card_no == "0":
                return None
            password = input("请输入密码：").strip()
            member = self.members.get(card_no)
            if member is not None and member.check_password(password):
                return member
            print("登录失败：卡号不存在或密码错误，请重新输入")

    # 登录后展示功能菜单
    @staticmethod
    def show_menu() -> None:
        print("\n---------------- 书海灯塔·主菜单 ----------------")
        print("1. 借阅图书")
        print("2. 归还图书")
        print("3. 查看我的借阅")
        print("0. 退出系统")
        print("------------------------------------------------")

    # 借阅图书：先验上限，再验编号与库存，成功后库存-1并保存
    def borrow_book(self, member: Member) -> None:
        print("\n当前藏书列表：")
        for book in self.books.values():
            tag = "可借" if book.is_available() else "无库存"
            print(f"{book.book_id}\t《{book.title}》\t{book.author}\t"
                  f"总数{book.total} 可用{book.available}\t[{tag}]")

        if member.is_borrow_full():
            print(f"借阅失败：{member.get_name()} 已借 {len(member.borrowed_books)} 本，"
                  f"达到最大可借数量（{member.get_max_borrow()} 本），请先归还再继续借阅")
            return

        book_id = input("请输入要借阅的图书编号（输0取消）：").strip()
        if book_id == "0":
            return
        # 查找结果单独用 target_book 承接：它的类型是 Book | None，
        # 不能复用上方展示循环的 book（已确定为 Book），否则类型冲突
        target_book = self.books.get(book_id)
        if target_book is None:
            print("借阅失败：图书编号不存在，请核对后重试")
            return
        if not target_book.is_available():
            print(f"借阅失败：《{target_book.title}》可用数量为 0，暂无库存可借")
            return

        target_book.borrow()
        member.borrowed_books.append(target_book)
        self.save_data()
        print(f"借阅成功：{member.get_name()} 成功借阅《{target_book.title}》，"
              f"该馆尚余 {target_book.available} 本，您已借 {len(member.borrowed_books)}/{member.get_max_borrow()} 本")

    # 归还图书：只能归还自己借阅记录中的书，成功后库存+1并保存
    def return_book(self, member: Member) -> None:
        if not member.borrowed_books:
            print("归还失败：您当前没有在借的图书")
            return

        print("\n我的在借图书：")
        for book in member.borrowed_books:
            print(f"{book.book_id}\t《{book.title}》")

        book_id = input("请输入要归还的图书编号（输0取消）：").strip()
        if book_id == "0":
            return

        back_book = None
        for book in member.borrowed_books:
            if book.book_id == book_id:
                back_book = book
                break
        if back_book is None:
            print("归还失败：该编号不在您的借阅记录中")
            return

        back_book.return_back()
        member.borrowed_books.remove(back_book)
        self.save_data()
        print(f"归还成功：《{back_book.title}》已归还，该馆现有可用 {back_book.available} 本")

    # 查看我的借阅
    @staticmethod
    def show_borrowed(member: Member) -> None:
        print(f"\n【{member.get_name()}】的借阅列表"
              f"（已借 {len(member.borrowed_books)} / 最大可借 {member.get_max_borrow()} 本）：")
        if not member.borrowed_books:
            print("（暂无借阅记录）")
            return
        for index, book in enumerate(member.borrowed_books, start=1):
            print(f"{index}. {book.book_id}\t《{book.title}》\t{book.author}")

    # 程序入口：加载数据 -> 登录 -> 菜单循环
    def run(self) -> None:
        print("=" * 48)
        print("欢迎使用《书海灯塔 · 命令行图书借阅系统》")
        print("=" * 48)

        self.load_data()
        member = self.login()
        if member is None:
            print("已退出系统，再见！")
            return

        print(f"登录成功，欢迎 {member.get_name()}！您最多可借阅 {member.get_max_borrow()} 本")
        while True:
            self.show_menu()
            choice = input("请输入功能编号：").strip()
            if choice == "1":
                self.borrow_book(member)
            elif choice == "2":
                self.return_book(member)
            elif choice == "3":
                self.show_borrowed(member)
            elif choice == "0":
                print("已退出图书借阅系统，欢迎再次光临！")
                break
            else:
                print("输入有误，请输入 0/1/2/3 对应的编号")


# 直接运行本文件时启动系统
if __name__ == "__main__":
    LibrarySystem().run()
