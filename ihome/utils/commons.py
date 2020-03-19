from werkzeug.routing import BaseConverter
# 定义转换器
# 步骤：
# 1.导入转换器基类
# 2.定义转换器类，需要继承自基础转换器类
# 3.定义函数，接收参数，即正则表达式
# 4.添加到默认的转换器字典容器中

class RegexConverter(BaseConverter):

    def __init__(self,url_map,*args):
        super(RegexConverter, self).__init__(url_map)
        self.regex = args[0]


from flask import session,g,jsonify
from ihome.utils.response_code import RET
import functools
# 实现登录验证装饰器
# 步骤：
# 1.使用session对象，从redis中取出缓存的用户信息
# 2.判断获取结果，如果用户登录，利用g对象保存用户id
# 3.否则，用户未登录

def login_required(f):
    # @functools.wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get('user_id')
        if user_id is None:
            return jsonify(errno=RET.SESSIONERR,errmsg='用户未登录')
        else:
            g.user_id = user_id
            return f(*args,**kwargs)
    # python装饰器：会默认修改函数的属性，__name__属性就是函数的名称
    # 让被装饰的函数的函数名，赋值给内部函数，先修改wrapper的函数名
    wrapper.__name__ = f.__name__
    return wrapper
