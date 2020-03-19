# 导入蓝图
from flask import Blueprint
# 创建蓝图
api = Blueprint('api',__name__)

# 把使用蓝图对象的文件，导入到创建蓝图对象的下面
from . import passport,users,house

# 定义请求钩子，实现后台返回响应指定响应的类型，json格式
@api.after_request
def after_request(response):

    # 如果响应的头信息是text/html
    if response.headers.get('Content-Type').startswith('text'):
        response.headers['Content-Type'] = 'application/json'
    return response
