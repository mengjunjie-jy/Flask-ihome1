from flask import session,jsonify,current_app,request,g
# 导入蓝图
from . import api
from ihome.utils.response_code import RET
from ihome import redis_store,constants,db
# 导入模型类
from ihome.models import Area,House,Facility,HouseImage,User
import json

from ihome.utils.commons import login_required
from ihome.utils.image_storage import storage


@api.route('/session',methods=['GET'])
def check_user_login():
    """
    检查用户登录状态
    1.使用session对象，从redis中获取缓存的用户信息
    2.如果有，返回用户信息
    3.否则，返回默认信息
    :return:
    """
    name = session.get('name')
    if name is not None:
        return jsonify(errno=RET.OK,errmsg='OK',data={'name':name})
    else:
        return jsonify(errno=RET.SESSIONERR,errmsg='False')

@api.route('/areas',methods=['GET'])
def get_area_info():
    """
    城区信息加载：缓存---磁盘---缓存
    1.读取redis数据城区信息
    2.判断获取结果，如果有数据，直接返回城区信息
    因为城区信息是动态加载，不同时间访问，数据有可能会有差距，需要记录访问信息
    3.否则，读取Mysql数据库中保存的城区数据
    4.判断mysql查询结果，如果没数据，直接返回
    5.遍历查询结果，因为flask_sqlalchemy返回的是对象，
        需要调用模型类中to_dict方法，把对象转成字典数据
    6.把城区数据，转成json，存入redis中
    7.返回城区信息

    :return:
    """

    try:
        areas = redis_store.get('area_info')
    except Exception as e:
        current_app.logger.error(e)
        areas = None
    # 如果redis中有城区信息
    if areas:
        # 因为城区信息是动态加载，不同时间访问，数据有可能会有差距，需要记录访问信息
        current_app.logger.info('hit redis areas info')
        # 从redis中取出的数据，就是json，可以拼接字符串返回
        return '{"errno":"0","errmsg":"OK","data":%s}' % areas
    # 查询mysql
    try:
        areas = Area.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询城区信息失败')
    # 判断查询结果
    if areas is None:
        return jsonify(errno=RET.NODATA,errmsg='无城区信息')
    # 遍历城区列表信息，把查询对象，转成字典数据
    areas_list = []
    for area in areas:
        areas_list.append(area.to_dict())
    # 把城区信息转成json，存入redis中
    areas_json = json.dumps(areas_list)
    try:
        redis_store.setex('area_info',constants.AREA_INFO_REDIS_EXPIRES,areas_json)
    except Exception as e:
        current_app.logger.error(e)
    # 拼接json数据，进行返回
    resp = '{"errno":"0","errmsg":"OK","data":%s}' % areas_json
    return resp

@api.route('/houses',methods=['POST'])
@login_required
def save_house_info():
    """
    发布新房源
    1.获取参数，g.user_id,房屋的基本信息，配套设施
    2.判断json数据包是否存在
    3.获取详细参数信息
    4.判断房屋基本信息参数的完整性
    5.价格参数处理：前端价格以元为单位，后端数据保存以分为单位
    6.构造模型类对象，保存房屋数据
    7.判断配套设施参数，如有保存信息
    8.提交数据
    9.返回结果，房屋id

    :return:
    """
    # 获取json数据包
    json_data = request.get_json()
    if not json_data:
        return jsonify(errno=RET.PARAMERR,errmsg='参数错误')
    # 提取房屋参数信息
    area_id = json_data.get('area_id')
    title = json_data.get('title')
    price = json_data.get('price')
    address = json_data.get('address')
    room_count = json_data.get('room_count')
    acreage = json_data.get('acreage')
    unit = json_data.get('unit')
    capacity = json_data.get('capacity')
    beds = json_data.get('beds')
    deposit = json_data.get('deposit')
    min_days = json_data.get('min_days')
    max_days = json_data.get('max_days')
    # 判断参数完整性
    if not all([area_id,title,price,address,room_count,acreage,unit,capacity,beds,deposit,min_days,max_days]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    # 对价格参数单位进行转换,统一转成单位分
    try:
        price = int(float(price) * 100)
        deposit = int(float(deposit) * 100)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR,errmsg='金额格式错误')
    # 保存房屋信息
    house = House()
    house.user_id = g.user_id
    house.area_id = area_id
    house.title = title
    house.price = price
    house.address = address
    house.room_count = room_count
    house.acreage = acreage
    house.unit = unit
    house.capacity = capacity
    house.beds = beds
    house.deposit = deposit
    house.min_days = min_days
    house.max_days = max_days
    # 尝试获取房屋配套设施参数
    facility = json_data.get('facility')
    if facility:
        # 对配套设施进行校验，该设施在数据库有存储，in_是对设施范围进行判断
        try:
            facilities = Facility.query.filter(Facility.id.in_(facility)).all()
            house.facilities = facilities
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR,errmsg='查询房屋设施信息失败')
    # 提交数据
    try:
        db.session.add(house)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')
    # 返回结果
    return jsonify(errno=RET.OK,errmsg='OK',data={'house_id':house.id})

    pass


@api.route('/houses/<int:house_id>/images',methods=['POST'])
@login_required
def save_house_image(house_id):
    """
    保存房屋图片
    1.获取图片参数，house_image
    2.根据房屋id参数，确认房屋的存在
    3.读取图片数据，调用七牛云，上传图片
    4.保存房屋图片数据，房屋图片表和房屋表
    5.拼接房屋图片的绝对地址
    6.返回图片的url

    :param house_id:
    :return:
    """
    image = request.files.get('house_image')
    if not image:
        return jsonify(errno=RET.PARAMERR,errmsg='参数错误')
    # 根据路径参数房屋id，查询房屋
    try:
        house = House.query.get(house_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询房屋数据失败')
    if not house:
        return jsonify(errno=RET.NODATA,errmsg='无房屋数据')
    # 读取图片数据
    image_data = image.read()
    try:
        image_name = storage(image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR,errmsg='上传图片失败')
    # 保存房屋图片数据,房屋表，房屋图片表
    house_image = HouseImage()
    house_image.house_id = house.id
    house_image.url = image_name
    db.session.add(house_image)
    # 如果房屋未设置主图片
    if not house.index_image_url:
        house.index_image_url = image_name
        db.session.add(house)
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存数据失败')
    # 拼接图片的绝对路径
    image_url = constants.QINIU_DOMIN_PREFIX + image_name
    return jsonify(errno=RET.OK,errmsg='OK',data={'url':image_url})

    pass


@api.route('/user/houses',methods=['GET'])
@login_required
def get_user_houses():
    """
    获取用户发布的房屋信息
    :return:
    """
    # 获取用户身份id
    user_id = g.user_id
    # 查询用户数据
    try:
        user = User.query.get(user_id)
        # 使用模型类中的relationship关系引用
        houses = user.houses
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询错误')
    # 如果用户发布了房屋信息，遍历查询结果
    houses_list = []
    if houses:
        for house in houses:
            houses_list.append(house.to_basic_dict())
    # 返回结果
    return jsonify(errno=RET.OK,errmsg='OK',data={'houses':houses_list})
    pass


@api.route('/houses/index',methods=['GET'])
def get_houses_index():
    """
    获取首页房屋幻灯片信息：缓存---磁盘---缓存
    1.尝试从redis中获取房屋信息
    2.如果有数据，留下访问记录，拼接字符串返回json数据
    3.查询mysql，房屋：成交量较高的
    4.遍历查询结果，判断房屋是否有主图片，默认操作：无图不添加数据
    5.把列表存入redis中
    6.返回房屋信息

    :return:
    """
    try:
        ret = redis_store.get('house_page_data')
    except Exception as e:
        current_app.logger.error(e)
        ret = None
    if ret:
        current_app.logger.info('hit redis house index info')
        return '{"errno":"0","errmsg":"OK","data":%s}' % ret
    # 查询磁盘数据库,默认操作，按照成交次数排序查询
    try:
        houses = House.query.order_by(House.order_count.desc()).limit(constants.HOME_PAGE_MAX_HOUSES)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询房屋信息错误')
    if not houses:
        return jsonify(errno=RET.NODATA,errmsg='无房屋数据')
    # 定义容器，存储查询结果
    houses_list = []
    for house in houses:
        if not house.index_image_url:
            continue
        houses_list.append(house.to_basic_dict())
    # 转成json存入redis中
    houses_json = json.dumps(houses_list)
    try:
        redis_store.setex('home_page_data',constants.HOME_PAGE_DATA_REDIS_EXPIRES,houses_json)
    except Exception as e:
        current_app.logger.error(e)
    # 拼接响应数据
    resp = '{"errno":"0","errmsg":"OK","data":%s}' % houses_json
    return resp
