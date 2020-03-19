# 导入redis扩展
from redis import StrictRedis
# 开发项目，不同的环境，需要使用的配置是不同的，利用python面向对象的特点，把配置进行封装

class DefaultConfig(object):
    DEBUG = None

    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379

    # 设置密钥
    # 配置数据库的连接,需要创建数据库
    # 配置服务器中session信息存储的位置，redis数据库,session有效期默认不过期
    SECRET_KEY = 'itcast_python_flask'
    SQLALCHEMY_DATABASE_URI = 'mysql://root:mysql@localhost/ihome1'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TYPE = 'redis'
    SESSION_REDIS = StrictRedis(host=REDIS_HOST,port=REDIS_PORT)
    SESSION_USE_SIGNER = True
    PERMANENT_SESSION_LIFETIME = 86400 # Flask源码中，默认是31天

# 开发环境下的配置
class DevelopmentConfig(DefaultConfig):
    DEBUG = True

# 生产环境下的配置
class ProductionConfig(DefaultConfig):
    DEBUG = False

# 定义不同环境配置的字典映射
config_dict = {
    'dev': DevelopmentConfig,
    'pro': ProductionConfig
}
