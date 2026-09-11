#案例1

#目标:开发一个购物车系统，实现商品信息的添加修改删除和查询功能。

#要求1:添加购物车，即用户根据提示输入商品名称以及其价格和数量，保存该商品信息到购物车。
#要求2:修改购物车，即用户根据提示输入要修改的商品名称以及其价格和数量，保存该商品信息到购物车。
#要求3:删除购物车，即用户根据提示输入要删除的购物车名称，根据名称删除购物车中的商品
#要求4:查询购物车，将购物车的商品信息展示出来，格式为"商品名称:""商品价格:""商品数量:"

#1.制作购物车

shopping_cart = {}

#2..制作菜单

menu = '''
############### 欢迎使用购物车系统~ ###############
#                1.添加购物车                   # 
#                2.修改购物车                   # 
#                3.删除购物车                   # 
#                4.查询购物车                   # 
#                5.退出购物车                   # 
'''


#3.执行具体操作

while True:
    print(menu)
    choice = int(input('请输入要执行的操作(1-5):'))

    match choice:
        case 1:  # 添加购物车
            goods_name = input('请输入商品的名称：')
            goods_price = float(input('请输入商品的价格：'))
            goods_num = int(input('请输入商品的数量：'))

            # 如果商品已经存在，则不执行添加，并提示信息。

            if goods_name in shopping_cart:
                print('您输入的商品已经储存过名称信息了')
            else:
                shopping_cart[goods_name] = {'price': goods_price, 'num': goods_num}
                print('商品添加完毕')
        case 2:  # 修改购物车
            goods_name = input('请输入最新的商品名称：')
            goods_price = float(input('请输入最新的商品价格：'))
            goods_num = int(input('请输入最新的商品数量：'))

            if goods_name not in shopping_cart:
                print('您输入的商品不存在，请重新输入')
            else:
                shopping_cart[goods_name] = {'price': goods_price, 'num': goods_num}
                print('商品信息修改完毕')
        case 3:  # 删除购物车
            goods_name = input('请输入要删除商品的名称：')

            # 如果商品不存在，则提示错误信息，请重新选择。

            if goods_name not in shopping_cart:
                print('您输入的商品不存在，请重新输入')
            else:
                del shopping_cart[goods_name]
                print('商品信息删除完毕')
        case 4:  # 查询购物车
            for goods_name in shopping_cart:
                goods_info = shopping_cart[goods_name]
                print(f'商品名称：{goods_name},商品价格：{goods_info['price']},商品数量：{goods_info['num']}')
        case 5:  # 退出购物车
            print('感谢您的使用')
            break
        case _:
            print('非法输入！')




