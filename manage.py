# 脚本管理器和数据库迁移的扩展
from flask_script import Manager
from flask_migrate import Migrate,MigrateCommand
from ihome import create_app,db,models


app = create_app('dev')

# 实例化管理器对象
manage = Manager(app)
# 使用迁移框架
Migrate(app,db)
# 给脚本管理器，添加迁移命令
manage.add_command('db',MigrateCommand)

"""
Flask目录创建的思想：
1.首先实现入口文件，在入口文件中，实现基本程序
2.在基本程序中，补充业务相关扩展包的使用;(数据库扩展、脚本管理器、迁移等)
3.定义配置信息
4.代码拆分，先把配置文件拆分出去
5.再把初始化操作，拆分出去，定义工厂函数
6.把视图代码拆分出去

"""

if __name__ == '__main__':
    # app.run()
    print(app.url_map)
    manage.run()