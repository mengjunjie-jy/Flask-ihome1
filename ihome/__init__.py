from flask import Flask
# 导入flask-sqlalchemy扩展
from flask_sqlalchemy import SQLAlchemy
# 状态保持方案session信息的存储,指定服务器中session信息存储的位置
from flask_session import Session
# 导入配置类
from config import config_dict,DefaultConfig
# 导入日志模块
import logging
from logging.handlers import RotatingFileHandler
# 导入redis工具
from redis import StrictRedis
# 使用flask-wtf扩展，实现csrf保护
from flask_wtf import CSRFProtect

# 初始化redis，用来保存业务相关数据，比如：验证码、房屋信息等
redis_store = StrictRedis(host=DefaultConfig.REDIS_HOST,port=DefaultConfig.REDIS_PORT,decode_responses=True)
db = SQLAlchemy()
csrf = CSRFProtect()

# 集成项目日志
# 设置日志的记录等级
logging.basicConfig(level=logging.DEBUG)  # 调试debug级
# 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024*1024*100, backupCount=10)
# 创建日志记录的格式                 日志等级    输入日志信息的文件名 行数    日志信息
formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
# 为刚创建的日志记录器设置日志记录格式
file_log_handler.setFormatter(formatter)
# 为全局的日志工具对象（应用程序实例app使用的）添加日后记录器
logging.getLogger().addHandler(file_log_handler)


# 封装程序初始化的操作，定义工厂函数，代码封装，
# 可以根据函数的参数，动态的指定程序实例使用不同环境下的配置，生产不同环境下的app
def create_app(config_name):
    app = Flask(__name__)
    # 使用配置对象
    app.config.from_object(config_dict[config_name])
    db.init_app(app)
    Session(app)
    # 让flask-wtf扩展和flask程序实例app关联，实现csrf保护
    csrf.init_app(app)

    # 导入自定义的转换器
    from ihome.utils.commons import RegexConverter
    app.url_map.converters['regex'] = RegexConverter

    # 导入静态资源访问的蓝图
    from ihome.web_page import html as html_blueprint
    app.register_blueprint(html_blueprint)

    # 导入蓝图对象，注册蓝图对象给程序实例app
    from ihome.api_1_0 import api as api_blueprint
    app.register_blueprint(api_blueprint,url_prefix='/api/v1.0')



    # 只能返回一个对象
    return app