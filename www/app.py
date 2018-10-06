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
# 创建aiohttp.web.request实例
def index(request):
    # 创建aiohttp.web.response实例
    return web.Response(body=b'<h1>This is MySite</h1>', content_type='text/html')

# 二，创建Web服务器，并将处理函数注册进其应用路径(Application.router)
# 创建Web服务器实例app，也就是aiohttp.web.Application类的实例，该实例的作用是处理URL、HTTP协议
@asyncio.coroutine
def init(loop):
    app = web.Application()
    app.router.add_route('GET', '/', index)
    srv = yield from loop.create_server(app._make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()