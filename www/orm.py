#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import aiomysql		# 异步mysql驱动支持
import logging		# 支持日志操作
import asyncio
import pdb

def log(sql, args=()):
    # 该函数用于打印执行的SQL语句
    logging.info('SQL:%s' % sql)

async def create_pool(loop, **kw):
    # 该函数用于创建连接池
    global __pool # 全局变量用于保存连接池
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'), # 默认定义host名字为localhost
        port=kw.get('port', 3306),          # 默认定义mysql的默认端口是3306
        user=kw['user'],            # user是通过关键字参数传进来的
        password=kw['password'],        # 密码也是通过关键字参数传进来的
        db=kw['database'],              # 数据库名字，如果做orm测试的使用请使用db=kw['db']
        charset=kw.get('charset', 'utf8'),     # 默认数据库字符集是utf8,注意没有‘-’
        autocommit=kw.get('autocommit', True),  # 默认自动提交事务
        maxsize=kw.get('maxsize', 10),      # 连接池最多同时处理10个请求
        minsize=kw.get('minsize', 1),        # 连接池最少1个请求
        loop=loop                           # 传递消息循环对象loop用于异步执行
    )


# =============================SQL处理函数区==========================
# select和execute方法是实现其他Model类中SQL语句都经常要用的方法，原本是全局函数，这里作为静态函数处理
# 注意：之所以放在Model类里面作为静态函数处理是为了更好的功能内聚，便于维护，这点与廖老师的处理方式不同，请注意

async def select(sql, args, size=None):
    # select语句则对应该select方法，传入sql语句和参数
    log(sql, args)
    global __pool # 这里声明global，是为了区分赋值给同名的局部变量（这里其实可以省略，因为后面没赋值）
    # 异步等待连接池对象返回可以连接的线程，with语句则封装了清理（关闭conn）和处理异常工作
    with (await __pool) as conn:
        # 等待连接对象返回DictCursor可以通过dict的方式获取数据库对象，需要通过游标对象执行SQL
        cur = await conn.cursor(aiomysql.DictCursor)
        # 所有args都通过replace方式把占位符替换成%s
        # args是execute方法的参数
        await cur.execute(sql.replace('?', '%s'), args or ())
        # pdb.set_trace()
        if size:    # 如果指定要返回几行
            rs = await cur.fetchmany(size)  # 从数据库获取指定的行数
        else:       # 如果没指定返回几行，即size=None
            rs = await cur.fetchall()       # 返回所有结果集
        await cur.close()       # 都要异步执行
        logging.info('rows returned: %s' % len(rs))     # 输出log信息
        return rs           # 返回结果集

async def execute(sql, args, autocommit=True):
    # execute方法只返回结果函数，不返回结果集，用于insert,update，delete这些SQL语句
    log(sql)
    with (await __pool) as conn:
        if not autocommit:
            await conn.begin()
        try:
            cur = await conn.cursor()
            # 执行sql语句，同时替换占位符
            # pdb.set_trace()
            await cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount     # 返回受影响的行数
            await cur.close()           # 关闭游标
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise e         # raise不带参数，则把此处的错误往上抛，为了方便理解建议加e
        return affected


# ========================================Model基类以及具其元类=====================
# 对象和关系（数据库?）之间要映射起来，首先考虑创建所有Model类的一个父类，具体的Model对象（就是数据库表在你代码中对应的对象）再继承这个基类

class ModelMetaclass(type):
    # 该元类主要使得Model基类具备以下功能：
    # 1.任何继承自Model的类（比如user），会自动通过ModelMetaclass扫描映射关系
    # 并存储到自身的类属性如__table__、__mapping__中
    # 2.创建了一些默认的SQL语句

    def __new__(cls, name, bases, attrs):
        # 排除Model这个基类
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        # 获取table名称，一般就是Model的类的名称
        tableName = attrs.get('__table__', None) or name    # 前面get失败了就赋值name
        logging.info('found model:%s (table:%s)' % (name, tableName))
        # 获取所有的Field和主键名
        mappings = dict()       # 保存属性和值的k,v（创建映射字典)
        fields = []             # 保存Model类的属性（域list）
        primaryKey = None       # 保存Model类的主键
        for k, v in attrs.items():
            if isinstance(v, Field):    # 如果是Field类型的则加入mappings对象
                logging.info('found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                # k, v键值对全部保存到mappings中，包括主键和非主键
                if v.primary_key:       # 如果v是主键即primary_key=True，尝试把其赋值给primaryKey属性
                    if primaryKey:      # 如果primaryKey属性已经不为空了，说明已经有主键了，则抛出错误，因为只能有1个主键
                        raise RuntimeError(
                            'Duplicate primary key for field: %s' % k
                        )
                    primaryKey = k      # 如果主键还没被赋值过，则直接赋值
                else:      # v不是主键，即primary_key=False的情况
                    fields.append(k)    # 非主键全部放到fields列表中
        if not primaryKey:      # 如果遍历完还没有找到主键，则抛出错误
            raise RuntimeError('Primary key not found')
        for k in mappings.keys():       # 清除mappings，防止实例属性覆盖类的同名属性，造成运行时错误
            # attrs中对应的属性则需要删除，作者指的是attrs的属性和mappings中的属性发生冲突，具体原因可能需要自己体验下这个错误才知道
            attrs.pop(k)

        # %s占位符全部替换成具体属性名
        escaped_fields = list(map(lambda f: r"'%s'" % f, fields))

        # ======初始化私有的特别属性======
        attrs['__mappings__'] = mappings  # 保存属性和列的关系，赋值给特殊类变量__mappings__
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey
        attrs['__fields__'] = fields

        # ======构造默认的select,insert,update,delete语句======
        # 这里据说不用`，在mysql里会报错，待验证
        # 默认的select语句貌似没怎么被用到，如果通用性不好，可能不如不加，后面就findAll方法用到了
        attrs['__select__'] = "select '%s',%s from '%s'" % (
            primaryKey, ','.join(escaped_fields, tableName)
        )
        # insert语句前面有3个占位符，所以从第四个%开始应该是（用于替换第一个值的a1，替换第二个值的a2，替换第三个值的a3）
        # 默认想执行的应该是update tableName set 属性1=?，属性2=?，……where 主键=primary_key
        # a1是tableName没问题，a2应该是主键的属性，a3则通过过匿名函数结合map将%s=?全部替换成属性名=?
        # 因此这里的匿名函数就是讲%s这个占位符替换成'属性名'=?
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName,', '.join(
            map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        # 第三个占位符有很多问号，为了方便就直接使用了create_ars_string函数来生成num个占位符的string
        # pdb.set_trace()
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ','.join(
            escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        return type.__new__(cls, name, bases, attrs)


def create_args_string(num):        # 在ModelMetaclass的特殊变量中用到
    # insert插入属性的时候，增加num个数量的占位符'?'
    L = []
    for n in range(num):
        L.append('?')
    return ','.join(L)


class Model(dict, metaclass=ModelMetaclass):
    # 继承dict是为了使用方便，例如对象实例user['id']即可轻松通过UserModel去数据库获取到id
    # 元类自然是为了封装我们之前写的具体的SQL处理函数，从数据库获取数据

    def __init__(self, **kw):
        # 调用dict的父类__init__方法用于创建Model，super（类名，类对象）
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        # 调用不存在的属性时返回一些内容
        try:
            return self[key]    # 如果存在则正常返回
        except KeyError:
            raise AttributeError(r"'Model' object has no attribut '%s'" % key)

    def __setattr__(self, key, value):
        # 设定Model里面的key-value对象，这里value允许为None
        self[key] = value

    def getValue(self,key):
        #
