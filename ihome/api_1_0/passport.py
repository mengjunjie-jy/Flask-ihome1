from flask import current_app,jsonify,make_response,request,session
# 导入蓝图对象
from . import api
# 导入captcha工具包
from ihome.utils.captcha.captcha import captcha
# 导入数据库
from ihome import redis_store,constants,db
# 导入自定义的状态码信息
from ihome.utils.response_code import RET
# 导入正则模块
import re
# 导入模型类
from ihome.models import User
# 导入随机数模块
import random
# 导入云通讯
from ihome.utils.sms import CCP


@api.route("/imagecode/<image_code_id>",methods=['GET'])
def generate_image_code(image_code_id):
    """
    生成图片验证码
    1.导入captcha工具包
    2.生成图片验证码，获取文本和图片
    3.存入redis数据库中，存文本
    4.返回前端图片，把响应类型改成image/jpg
    :param image_code_id:
    :return:
    """
    text,image = captcha.generate_captcha()
    # 在redis中保存图片验证码文本
    try:
        redis_store.setex('ImageCode_' + image_code_id,constants.IMAGE_CODE_REDIS_EXPIRES,text)
    except Exception as e:
        # 使用应用上下文对象，记录项目日志
        current_app.logger.error(e)
        # 返回错误信息,前后端数据交互格式应该使用json
        return jsonify(errno=RET.DBERR,errmsg='数据保存失败')
    else:
        resp = make_response(image)
        resp.headers['Content-Type'] = 'image/jpg'
        return resp

@api.route('/smscode/<mobile>',methods=['GET'])
def send_sms_code(mobile):
    """
    发送短信：获取参数---检查参数---业务处理---返回结果
    1.获取参数，查询字符串方式，图片验证码和编号
    2.检查参数的完整性
    3.正则校验参数的格式
    4.从redis中取出真实的图片验证码内容
    5.判断redis中的获取结果
    6.先把redis中的图片验证码内容删除
    7.比较图片验证码是否正确
    8.生成短信的随机码，存入redis中
    9.调用云通讯发送短信
    10.判断发送结果是否成功

    :param mobile:text:id
    :return:
    """
    # 获取参数，查询字符串方式，图片验证码和编号
    image_code = request.args.get('text')
    image_code_id = request.args.get('id')
    # 检查参数的完整性
    if not all([mobile,image_code,image_code_id]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    # 校验手机号
    if not re.match(r'1[3-9]\d{9}',mobile):
        return jsonify(errno=RET.PARAMERR,errmsg='手机号格式错误')
    #### 手机号是否注册
    # 从redis中取出真实的图片验证码文本内容
    try:
        real_image_code = redis_store.get('ImageCode_' + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询数据失败')
    # 判断获取结果
    if not real_image_code:
        return jsonify(errno=RET.NODATA,errmsg='数据不存在')
    # 删除图片验证码
    try:
        redis_store.delete('ImageCode_' + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
    # 比较图片验证码
    if real_image_code.lower() != image_code.lower():
        return jsonify(errno=RET.DATAERR,errmsg='图片验证码错误')
    # 图片验证成功,校验手机号是否已注册
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询用户信息失败')
    else:
        if user is not None:
            return jsonify(errno=RET.DATAEXIST,errmsg='手机号已注册')
    # 生成6位数的短信随机码
    sms_code = '%06d' % random.randint(1,999999)
    # 存入redis中
    try:
        redis_store.setex('SMSCode_' + mobile,constants.SMS_CODE_REDIS_EXPIRES,sms_code)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')
    # 调用云通讯发送短信,短信有效期一般是分钟
    try:
        sms = CCP()
        result = sms.send_template_sms(mobile,[sms_code,constants.SMS_CODE_REDIS_EXPIRES/60],1)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR,errmsg='发送短信异常')
    # 判断发送结果
    # if result == 0:
    if 0 == result:
        return jsonify(errno=RET.OK,errmsg='发送成功')
    else:
        return jsonify(errno=RET.THIRDERR,errmsg='发送失败')
    pass

@api.route('/users',methods=['POST'])
def register():
    """
    用户注册：本质是保存数据
    1.获取参数，
    2.检查参数的完整性
    3.校验手机号格式，手机号是否已注册
    4.从redis中获取真实的短信验证码，
    5.判断获取结果
    6.比较验证码是否正确
    7.删除redis中保存的短信验证码
    8.构造模型类对象，保存用户信息，提交数据
    9.在redis中缓存用户会话信息
    10.返回结果

    :return:mobile:sms_code,password
    """
    # 获取参数,post请求，前端已经把参数转成json格式
    # request.json.get('mobile') 根据key获取，只能获取一个参数
    # 获取整个json数据包
    json_data = request.get_json()
    if not json_data:
        return jsonify(errno=RET.PARAMERR,errmsg='参数错误')
    # 从json数据包中提取参数
    mobile = json_data.get('mobile')
    sms_code = json_data.get('sms_code')
    password = json_data.get('password')
    if not all([mobile,sms_code,password]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    # 校验手机号,是否注册
    if not re.match(r'1[3-9]\d{9}$', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='手机号格式错误')
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询用户信息失败')
    else:
        if user is not None:
            return jsonify(errno=RET.DATAEXIST,errmsg='手机号已注册')

    # 从redis中取出真实的短信验证码
    try:
        real_sms_code = redis_store.get('SMSCode_' + mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询数据失败')
    # 判断查询结果
    if not real_sms_code:
        return jsonify(errno=RET.NODATA,errmsg='数据已失效')
    # 先比较，再删除
    if real_sms_code != str(sms_code):
        return jsonify(errno=RET.DATAERR,errmsg='验证码错误')
    try:
        redis_store.delete('SMSCode_' + mobile)
    except Exception as e:
        current_app.logger.error(e)
    # 实例化模型类对象，保存用户信息
    user = User()
    user.mobile = mobile
    user.name = mobile
    user.password = password # 调用了模型类中的密码加密方法
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存用户信息失败')
    # 缓存用户信息,使用session对象，存到redis中
    session['user_id'] = user.id
    session['name'] = mobile
    session['mobile'] = mobile
    # 返回结果
    # data表示用户数据，是注册业务完成后，返回注册结果相关的附属信息
    return jsonify(errno=RET.OK,errmsg='注册成功',data=user.to_dict())

@api.route('/sessions',methods=['POST'])
def login():
    """
    用户登录：
    1.获取参数,json格式
    2.判断参数的完整性
    3.校验手机号格式
    4.根据手机号，查询mysql，确认用户已注册
    5.校验密码是否正确
    6.缓存用户信息，缓存用户的名称，而不是手机号
    7.返回结果

    :return:mobile,password
    """
    json_data = request.get_json()
    if not json_data:
        return jsonify(errno=RET.PARAMERR,errmsg='参数错误')
    # 从json数据包中提取数据
    mobile = json_data.get('mobile')
    password = json_data.get('password')
    if not all([mobile,password]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    # 校验手机号,是否注册
    if not re.match(r'1[3-9]\d{9}$', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='手机号格式错误')
    # 查询mysql
    try:
        user = User.query.filter(User.mobile==mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询数据失败')
    # 用户是否存在和密码是否正确，一起判断，返回模糊的错误信息
    if user is None or not user.check_password(password):
        return jsonify(errno=RET.DATAERR,errmsg='用户名或密码错误')
    # 缓存用户信息在redis中
    session['user_id'] = user.id
    session['mobile'] = mobile
    session['name'] = user.name # 用户有可能会修改用户名，默认用户名
    # 返回结果
    return jsonify(errno=RET.OK,errmsg='OK',data={'user_id':user.id})
    pass

