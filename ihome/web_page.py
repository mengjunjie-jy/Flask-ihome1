from flask_wtf import csrf

from flask import Blueprint,make_response,current_app
# 实现静态资源的优化访问
# 原访问路径：http://127.0.0.1:5000/static/html/register.html
# 优化后：http://127.0.0.1:5000/register.html

html = Blueprint('html',__name__)

@html.route('/<regex(".*"):file_name>')
def html_file(file_name):
    # 判断路由中是否有文件名
    if not file_name:
        file_name = 'index.html'

    # 判断是否访问的是logo图标，即favicon.ico文件
    if file_name != 'favicon.ico':
        file_name = 'html/' + file_name

    # 调用wtf扩展包，生成csrf-token
    csrf_token = csrf.generate_csrf()
    # 把文件发送给浏览器
    resp = make_response(current_app.send_static_file(file_name))

    # 给浏览器的cookie中，设置csrf_token值
    resp.set_cookie('csrf_token',csrf_token)

    return resp


    pass
