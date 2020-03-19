from flask import g,current_app,jsonify,request,session
# 导入蓝图
from . import api
# 导入登录验证装饰器
from ihome.utils.commons import login_required
# 导入模型类
from ihome.models import User
from ihome.utils.response_code import RET
# 导入七牛云
from ihome.utils.image_storage import storage
from ihome import db,constants


@api.route('/user',methods=['GET'])
@login_required
def get_user_profile():
    """
    获取用户信息
    1.从登录验证装饰器中的g对象，获取用户id
    2.查询用户数据
    3.判断查询结果，如未查到，直接返回
    4.返回用户信息
    :return:
    """
    user_id = g.user_id
    # 查询mysql
    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询错误')
    if not user:
        return jsonify(errno=RET.NODATA,errmsg='数据不存在')
    # 返回用户信息
    return jsonify(errno=RET.OK,errmsg='OK',data=user.to_dict())

    pass


@api.route('/user/avatar',methods=['POST'])
@login_required
def set_user_avatar():
    """
    设置用户头像
    1.获取参数，头像文件，前端form表单中input标签中的name属性
    2.校验参数
    3.读取图片文件，转成二进制
    4.调用七牛云接口，上传头像文件
    5.保存七牛云返回的图片名称，存入mysql数据库
    6.拼接图片的绝对路径：七牛云的空间域名+七牛云返回的图片名称
    7.返回图片路径
    :return:
    """
    # <文件对象>
    avatar = request.files.get('avatar')
    if not avatar:
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    # 读取图片数据
    image_data = avatar.read()
    # 调用七牛云
    try:
        image_name = storage(image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR,errmsg='保存文件失败')
    # 保存用户头像数据
    try:
        # user = User.query.get(g.user_id)
        # user.avatar_url = image_name
        # db.session.add(user)
        # db.session.commit()
        User.query.filter(User.id==g.user_id).update({'avatar_url':image_name})
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')
    # 拼接图片的绝对路径
    image_url = constants.QINIU_DOMIN_PREFIX + image_name
    # 返回图片链接
    return jsonify(errno=RET.OK,errmsg='OK',data={'avatar_url':image_url})

    pass

@api.route('/user/name',methods=['PUT'])
@login_required
def change_user_profile():
    # 获取参数，用户名
    name = request.json.get('name')
    if not name:
        return jsonify(errno=RET.PARAMERR,errmsg='参数错误')
    # 更新用户信息
    try:
        User.query.filter_by(id=g.user_id).update({'name':name})
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')
    # 更新缓存信息
    session['name'] = name
    # 返回数据
    return jsonify(errno=RET.OK,errmsg='OK',data={'name':name})

@api.route('/user/auth',methods=['POST'])
@login_required
def set_user_auth():
    """
    实名认证
    1.获取参数，json格式数据
    2.校验参数，参数是否存在，参数完整
    3.保存用户的实名信息
    4.返回结果

    :return:
    """
    json_data = request.get_json()
    if not json_data:
        return jsonify(errno=RET.PARAMERR,errmsg='参数错误')
    real_name = json_data.get('real_name')
    id_card = json_data.get('id_card')
    if not all([real_name,id_card]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    # 保存用户实名信息
    try:
        # 可以执行多次，实名认证可以修改
        # User.query.filter(User.id==g.user_id).update({'real_name':real_name,'id_card':id_card})
        # 执行一次
        User.query.filter(User.id==g.user_id,User.real_name==None,User.id_card==None).update({'real_name':real_name,'id_card':id_card})
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')
    # 返回结果
    return jsonify(errno=RET.OK,errmsg='OK')

    pass




    pass

@api.route('/user/auth',methods=['GET'])
@login_required
def get_user_auth():
    # 查询用户实名信息
    try:
        user = User.query.get(g.user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询错误')
    if not user:
        return jsonify(errno=RET.NODATA,errmsg='无效操作')
    # 返回用户实名信息
    return jsonify(errno=RET.OK,errmsg='OK',data=user.auth_to_dict())

@api.route('/session',methods=['DELETE'])
@login_required
def logout():
    """
    用户退出
    本质：清除用户在服务器中缓存的用户信息，即redis中的session信息
    :return:
    """
    user_id = g.user_id
    session.pop(user_id,None)
    # 不建议使用，clear方法，会把该用户的所有session信息全部清除
    # 400错误：csrf_token missing
    # csrf_token = session.get('csrf_token')
    # session.clear()
    # session['csrf_token'] = csrf_token
    return jsonify(errno=RET.OK,errmsg='OK')
