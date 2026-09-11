# 购物车系统（带确认机制 + 历史记录 + 输入容错）

shopping_cart = {}
history = []  # 用于保存操作历史

menu = '''
############### 欢迎使用购物车系统~ ###############
#                1.添加购物车                   # 
#                2.修改购物车                   # 
#                3.删除购物车                   # 
#                4.查询购物车                   # 
#                5.查看历史记录                 # 
#                6.退出购物车                   # 
'''

def confirm_action(prompt="确定执行该操作吗？(y/n)：") -> bool:
    """询问用户是否确认操作，返回 True(确认) 或 False(取消)"""
    while True:
        answer = input(prompt).strip().lower()
        if answer in ('y', 'yes', '是'):
            return True
        elif answer in ('n', 'no', '否'):
            return False
        else:
            print('输入无效，请输入 y 或 n。')

def get_float(prompt):
    """安全获取浮点数，输入非法时重新提示"""
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print('输入无效，请输入数字（例如 5.5）。')

def get_int(prompt):
    """安全获取整数，输入非法时重新提示"""
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print('输入无效，请输入整数（例如 3）。')

while True:
    print(menu)
    try:
        choice = int(input('请输入要执行的操作(1-6):'))
    except ValueError:
        print('请输入数字！')
        continue

    match choice:
        case 1:  # 添加购物车
            goods_name = input('请输入商品的名称：')
            goods_price = get_float('请输入商品的价格：')
            goods_num = get_int('请输入商品的数量：')

            if goods_name in shopping_cart:
                print('您输入的商品已经储存过名称信息了')
                continue

            if confirm_action('确定要添加该商品吗？(y/n)：'):
                shopping_cart[goods_name] = {'price': goods_price, 'num': goods_num}
                # 记录历史
                history.append(f"添加商品：{goods_name}，价格：{goods_price}，数量：{goods_num}")
                print('商品添加完毕')
            else:
                print('已取消添加')

        case 2:  # 修改购物车
            goods_name = input('请输入要修改的商品名称：')
            if goods_name not in shopping_cart:
                print('您输入的商品不存在，请重新输入')
                continue

            goods_price = get_float('请输入新的商品价格：')
            goods_num = get_int('请输入新的商品数量：')

            if confirm_action('确定要修改该商品信息吗？(y/n)：'):
                old_info = shopping_cart[goods_name]
                shopping_cart[goods_name] = {'price': goods_price, 'num': goods_num}
                # 记录历史
                history.append(f"修改商品：{goods_name}，价格由 {old_info['price']} 改为 {goods_price}，数量由 {old_info['num']} 改为 {goods_num}")
                print('商品信息修改完毕')
            else:
                print('已取消修改')

        case 3:  # 删除购物车
            goods_name = input('请输入要删除商品的名称：')
            if goods_name not in shopping_cart:
                print('您输入的商品不存在，请重新输入')
                continue

            if confirm_action('确定要删除该商品吗？(y/n)：'):
                old_info = shopping_cart[goods_name]
                del shopping_cart[goods_name]
                # 记录历史
                history.append(f"删除商品：{goods_name}，价格：{old_info['price']}，数量：{old_info['num']}")
                print('商品信息删除完毕')
            else:
                print('已取消删除')

        case 4:  # 查询购物车
            if not shopping_cart:
                print('购物车是空的')
            else:
                print('购物车商品信息如下：')
                for goods_name, info in shopping_cart.items():
                    print(f"商品名称：{goods_name}, 商品价格：{info['price']}, 商品数量：{info['num']}")

        case 5:  # 查看历史记录
            if not history:
                print('暂无历史记录')
            else:
                print('历史操作记录如下：')
                for idx, record in enumerate(history, 1):
                    print(f"{idx}. {record}")

        case 6:  # 退出购物车
            if confirm_action('确定要退出购物车系统吗？(y/n)：'):
                print('感谢您的使用，再见！')
                break
            else:
                print('继续使用')

        case _:
            print('非法输入！')