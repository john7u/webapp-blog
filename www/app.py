#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 所需第三方库：
# aiohttp，异步Web开发框架；jinja2，前端模板引擎；aiomysql，异步mysql数据库驱动
# 所需内置库：
# logging，系统日志；asyncio，异步IO；os，系统接口；json，json编码解码模块；time，系统时间模块；datetime，日期模块

import logging; logging.basicConfig(level=logging.INFO)
import asyncio, os, json, time
from datetime import datetime
from aiohttp import web

# 一，编写处理函数：
# 参数，aiohttp.web.request实例，包含了所有浏览器发送过来的 HTTP 协议里面的信息，一般不用自己构造
# 返回值，aiohttp.web.response实例，由web.Response(body='')构造，继承自StreamResponse，功能为构造一个HTTP响应
# 类声明，class aiohttp.web.Response(*, status=200, headers=None, content_type=None, body=None, text=None)
# HTTP协议格式为：POST /PATH /1.1 /r/n Header1:Value  /r/n .. /r/n HeaderN:Valule /r/n Body:Data

def index(request):
    return web.Response(body=b'<h1>This is MySite</h1>')

# 二，创建Web服务器，并将处理函数注册进其应用路径(Application.router)
# 1.创建Web服务器实例app，也就是aiohttp.web.Application类的实例，该实例的作用是处理URL、HTTP协议
# 1.1 Application，构造函数 def __init__(self, *, logger=web_logger, loop=None,
# router=None, handler_factory=RequestHandlerFactory,middlewares=(), debug=False):
# 1.2使用app时，首先要将URLs注册进router，再用aiohttp.RequestHandlerFactory 作为协议簇创建套接字(套接字=地址:端口号）
# 1.3 aiohttp.RequestHandlerFactory 可以用 make_handle() 创建，用来处理 HTTP 协议，接下来将会看到
# 2.将处理函数注册到创建app.router中
# 2.1 router，默认为UrlDispatcher实例，UrlDispatcher类中有方法
# add_route(method, path, handler, *, name=None, expect_handler=None)，
# 该方法将处理函数（其参数名为handler）与对应的URL（HTTP方法method，URL路径path）绑定，浏览器敲击URL时返回处理函数的内容

@asyncio.coroutine
def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', index)
    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv


loop = asyncio.get_event_loop()
loop.run_until_complete(init())
loop.run_forever()


