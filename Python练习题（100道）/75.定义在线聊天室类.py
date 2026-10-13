#定义一个简单的在线聊天室类，这个类允许用户加入聊天室、发送消息、查看聊天记录以及离开聊天室

#定义在线聊天室类

class ChatRoom:

    """用于模拟一个简单的聊天室，允许用户加入聊天室、发送消息、查看聊天记录以及离开聊天室"""

    def __init__(self):

        """初始化聊天室，设置空的用户列表和聊天记录列表"""
        print("欢迎使用在线聊天室")
        name = input("请输入聊天室名称：")
        self.name = name
        self.users = []
        self.messages = []

    def join(self, user):

        """
        用户加入聊天室
        :param user: 用户名
        :return:
        """

        #判断用户是否已经加入聊天室
        if user not in self.users:
            self.messages.append(f"{user} 加入聊天室")
            self.users.append(user)
            print(f"{user} 加入聊天室")
        else:
            self.messages.append(f"{user} 已经在聊天室中")
            print(f"{user} 已经在聊天室中")

    def leave(self, user):

        """
        用户离开聊天室
        :param user: 离开的用户
        :return:
        """

        #判断用户是否在聊天室中
        if user in self.users:
            self.messages.append(f"{user} 离开聊天室")
            self.users.remove(user)
            print(f"{user} 离开聊天室")
        else:
            self.messages.append(f"{user} 不在聊天室中")
            print(f"{user} 不在聊天室中")

    def send_message(self, user, message):

        """
        用户发送消息
        :param user: 用户名
        :param message: 消息内容
        :return:
        """

        #判断用户是否在聊天室中
        if user in self.users:
            self.messages.append(f"{user}: {message}")
            print(f"{user}: {message}")
        else:
            self.messages.append(f"{user} 不在聊天室中")

    def show_message(self):

        """
        显示聊天记录
        :return: None
        """

        #判断消息列表中是否有消息

        if self.messages:

            for message in self.messages:
                print(message)

        else:

            print('聊天室中没有消息！')

#示例使用

if __name__ == "__main__":

    chatroom = ChatRoom()

    # ---------- 场景一：用户加入聊天室 ----------
    print("\n" + "=" * 40)
    print("【场景一】用户加入聊天室")
    print("=" * 40)
    chatroom.join("Alice")
    chatroom.join("Bob")

    # ---------- 场景二：用户发送消息 ----------
    print("\n" + "=" * 40)
    print("【场景二】用户发送消息")
    print("=" * 40)
    chatroom.send_message("Alice", "Hello Bob!")
    chatroom.send_message("Bob", "Hi Alice!")

    # ---------- 场景三：查看当前聊天记录 ----------
    print("\n" + "=" * 40)
    print("【场景三】当前聊天记录")
    print("=" * 40)
    chatroom.show_message()

    # ---------- 场景四：用户离开聊天室 ----------
    print("\n" + "=" * 40)
    print("【场景四】Alice 和 Bob 离开聊天室")
    print("=" * 40)
    chatroom.leave("Alice")
    chatroom.leave("Bob")

    # ---------- 场景五：再次查看聊天记录 ----------
    print("\n" + "=" * 40)
    print("【场景五】离开后的完整聊天记录")
    print("=" * 40)
    chatroom.show_message()
