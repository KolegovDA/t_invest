# coding: utf-8
# для решения проблемы RuntimeError: main thread is not in main loop
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import time, math,sys
import datetime, traceback
import os, json, io
import sqlite3 as sq
#from key import test_net_api_key_bybit,test_net_trade_api_secret_key_bybit,kolegov_sub_eth_key,kolegov_sub_eth_secret,kolegov_sub_xrp_key,kolegov_sub_xrp_secret,bull_andrey_gushchin_key,bull_andrey_gushchin_secret
from threading import Thread
import threading
from collections import deque
from pybit.unified_trading import WebSocket
from pybit.unified_trading import HTTP
import telebot
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext,simpledialog
from PIL import ImageTk, Image  # pip install pillow
import hmac
import hashlib
import websocket
import certifi
import ssl
import pytz



##################################################
# ПРЕСЕТЫ для МОНЕТ. НАЧАЛО
##################################################

def coin_strategy(ticket):
    ##################################
    # Набор исходных данных в зависимости от выбранной пары
    ##################################
    if ticket == "ETHUSDT":
        # print(f"Работаем по стратегии {ticket}")
        grid_step = 0.5  # Шаг сетки - процент на который должна упасть цена для запуска входа в новый ордер
        grid_multiplikator = 1.6  # мультапликатор сетки
        trall_tp = 0.15  # Тралл TP 1% ТРАЛЛ ВХОДА. Это процент на которую должна поднятся цена после достижения уровня grid_step, для выставления лимитного ордера на вход в первый ордер сетки

        # min_order_amount = float(user_settings["symbol_list"][0][ticket]["user_minOrderAmt"])  # начальный ордер 10 баксов
        # if min_order_amount < 10:
        min_order_amount = 6
        max_order_amount = 3 * min_order_amount
        take_profit = 0.7  # тейк профит 1%
        max_take_profit = 5  # максимальный тейк профит, если достигаем этого уровня, то закрываем сделку
        sl_take_ptofit = 0.1  # если потеряем sl_take_ptofit тейкпрофита, то выходим
        take_profit = take_profit + sl_take_ptofit
        multiplikator = 1.05
        min_pure_profit = 0.125  # мин прибыль ордера под которую будет расчитываться динамический ТП = 0,25%

        max_order_qty = 20

        min_working_time_of_grid = 86400  # время после которого мы готовы закрывать сетку по условию прибыль =2х от убытков
        sleep_time = 120
        time_to_update_order_status = 5  # обновляем статус ордеров через каждые time_to_update_order_status секунд



    elif ticket == "XRPUSDT":
        # print(f"Работаем по стратегии {ticket}")
        grid_step = 0.5  # Шаг сетки - процент на который должна упасть цена для запуска входа в новый ордер
        grid_multiplikator = 1.6  # мультапликатор сетки
        trall_tp = 0.15  # Тралл TP 1% ТРАЛЛ ВХОДА. Это процент на которую должна поднятся цена после достижения уровня grid_step, для выставления лимитного ордера на вход в первый ордер сетки

        # min_order_amount = float(user_settings["symbol_list"][0][ticket]["user_minOrderAmt"])  # начальный ордер 10 баксов
        # if min_order_amount < 10:
        min_order_amount = 6
        max_order_amount = 3 * min_order_amount
        take_profit = 0.68  # тейк профит 1%
        max_take_profit = 5  # максимальный тейк профит, если достигаем этого уровня, то закрываем сделку
        sl_take_ptofit = 0.1  # если потеряем sl_take_ptofit тейкпрофита, то выходим
        take_profit = take_profit + sl_take_ptofit
        multiplikator = 1.05
        min_pure_profit = 0.125  # мин прибыль ордера под которую будет расчитываться динамический ТП = 0,25%

        max_order_qty = 20

        min_working_time_of_grid = 86400  # время после которого мы готовы закрывать сетку по условию прибыль =2х от убытков
        sleep_time = 120
        time_to_update_order_status = 5  # обновляем статус ордеров через каждые time_to_update_order_status секунд

    elif ticket == "BTCUSDT":
        # print(f"Работаем по стратегии {ticket}")
        grid_step = 0.6  # Шаг сетки - процент на который должна упасть цена для запуска входа в новый ордер
        grid_multiplikator = 1.28  # мультапликатор сетки
        trall_tp = 0.15  # Тралл TP 1% ТРАЛЛ ВХОДА. Это процент на которую должна поднятся цена после достижения уровня grid_step, для выставления лимитного ордера на вход в первый ордер сетки

        # min_order_amount = float(user_settings["symbol_list"][0][ticket]["user_minOrderAmt"])  # начальный ордер 10 баксов
        # if min_order_amount < 15:
        min_order_amount = 6
        max_order_amount = 3 * min_order_amount
        take_profit = 1.6  # тейк профит 1%
        max_take_profit = 3  # максимальный тейк профит, если достигаем этого уровня, то закрываем сделку
        sl_take_ptofit = 0.05  # если потеряем sl_take_ptofit тейкпрофита, то выходим
        take_profit = take_profit + sl_take_ptofit
        multiplikator = 1.05
        min_pure_profit = 0.125  # мин прибыль ордера под которую будет расчитываться динамический ТП = 0,25%

        max_order_qty = 20

        min_working_time_of_grid = 86400  # время после которого мы готовы закрывать сетку по условию прибыль =2х от убытков
        sleep_time = 120
        time_to_update_order_status = 5  # обновляем статус ордеров через каждые time_to_update_order_status секунд

    elif ticket == "LINKUSDT":
        # print(f"Работаем по стратегии {ticket}")
        grid_step = 0.7  # Шаг сетки - процент на который должна упасть цена для запуска входа в новый ордер
        grid_multiplikator = 1.5  # мультапликатор сетки
        trall_tp = 0.15  # Тралл TP 1% ТРАЛЛ ВХОДА. Это процент на которую должна поднятся цена после достижения уровня grid_step, для выставления лимитного ордера на вход в первый ордер сетки

        # min_order_amount = float(user_settings["symbol_list"][0][ticket]["user_minOrderAmt"])  # начальный ордер 10 баксов
        # if min_order_amount < 10:
        min_order_amount = 6
        max_order_amount = 3 * min_order_amount
        take_profit = 0.78  # тейк профит 1%
        max_take_profit = 10  # максимальный тейк профит, если достигаем этого уровня, то закрываем сделку
        sl_take_ptofit = 0.05  # если потеряем sl_take_ptofit тейкпрофита, то выходим
        take_profit = take_profit + sl_take_ptofit
        multiplikator = 1.05
        min_pure_profit = 0.125  # мин прибыль ордера под которую будет расчитываться динамический ТП = 0,25%

        max_order_qty = 20

        min_working_time_of_grid = 86400  # время после которого мы готовы закрывать сетку по условию прибыль =2х от убытков
        sleep_time = 120
        time_to_update_order_status = 5  # обновляем статус ордеров через каждые time_to_update_order_status секунд

    elif ticket == "TONUSDT":
        # print(f"Работаем по стратегии {ticket}")
        grid_step = 0.9  # Шаг сетки - процент на который должна упасть цена для запуска входа в новый ордер
        grid_multiplikator = 1.47  # мультапликатор сетки
        trall_tp = 0.15  # Тралл TP 1% ТРАЛЛ ВХОДА. Это процент на которую должна поднятся цена после достижения уровня grid_step, для выставления лимитного ордера на вход в первый ордер сетки

        # min_order_amount = float(user_settings["symbol_list"][0][ticket]["user_minOrderAmt"])  # начальный ордер 10 баксов
        # if min_order_amount < 10:
        min_order_amount = 6
        max_order_amount = 3 * min_order_amount
        take_profit = 0.7  # тейк профит 1%
        max_take_profit = 3  # максимальный тейк профит, если достигаем этого уровня, то закрываем сделку
        sl_take_ptofit = 0.1  # если потеряем sl_take_ptofit тейкпрофита, то выходим
        take_profit = take_profit + sl_take_ptofit
        multiplikator = 1.05
        min_pure_profit = 0.125  # мин прибыль ордера под которую будет расчитываться динамический ТП = 0,25%

        max_order_qty = 20

        min_working_time_of_grid = 86400  # время после которого мы готовы закрывать сетку по условию прибыль =2х от убытков
        sleep_time = 120
        time_to_update_order_status = 5  # обновляем статус ордеров через каждые time_to_update_order_status секунд

    elif ticket == "DOTUSDT":
        # print(f"Работаем по стратегии {ticket}")
        grid_step = 0.9  # Шаг сетки - процент на который должна упасть цена для запуска входа в новый ордер
        grid_multiplikator = 1.47  # мультапликатор сетки
        trall_tp = 0.15  # Тралл TP 1% ТРАЛЛ ВХОДА. Это процент на которую должна поднятся цена после достижения уровня grid_step, для выставления лимитного ордера на вход в первый ордер сетки

        # min_order_amount = float(user_settings["symbol_list"][0][ticket]["user_minOrderAmt"])  # начальный ордер 10 баксов
        # if min_order_amount < 10:
        min_order_amount = 6
        max_order_amount = 3 * min_order_amount
        take_profit = 0.7  # тейк профит 1%
        max_take_profit = 3  # максимальный тейк профит, если достигаем этого уровня, то закрываем сделку
        sl_take_ptofit = 0.1  # если потеряем sl_take_ptofit тейкпрофита, то выходим
        take_profit = take_profit + sl_take_ptofit
        multiplikator = 1.05
        min_pure_profit = 0.125  # мин прибыль ордера под которую будет расчитываться динамический ТП = 0,25%

        max_order_qty = 20

        min_working_time_of_grid = 86400  # время после которого мы готовы закрывать сетку по условию прибыль =2х от убытков
        sleep_time = 120
        time_to_update_order_status = 5  # обновляем статус ордеров через каждые time_to_update_order_status секунд

    elif ticket == "BNBUSDT":
        grid_step = 0.25
        grid_multiplikator = 1.75
        trall_tp = 0.15
        min_order_amount = 10
        max_order_amount = 3 * min_order_amount
        take_profit = 0.78
        max_take_profit = 5
        sl_take_ptofit = 0.05
        take_profit = take_profit + sl_take_ptofit
        multiplikator = 1.05
        min_pure_profit = 0.125  # мин прибыль ордера под которую будет расчитываться динамический ТП = 0,25%

        max_order_qty = 20

        min_working_time_of_grid = 86400
        sleep_time = 120
        time_to_update_order_status = 5

    elif ticket == "SOLUSDT":
        grid_step = 0.75
        grid_multiplikator = 1.485
        trall_tp = 0.15
        min_order_amount = 6
        max_order_amount = 3 * min_order_amount
        take_profit = 1.0
        max_take_profit = 5
        sl_take_ptofit = 0.1
        take_profit = take_profit + sl_take_ptofit
        multiplikator = 1.05
        min_pure_profit = 0.125  # мин прибыль ордера под которую будет расчитываться динамический ТП = 0,25%

        max_order_qty = 20

        min_working_time_of_grid = 86400
        sleep_time = 120
        time_to_update_order_status = 5

    elif ticket == "LTCUSDT":
        grid_step = 0.4
        grid_multiplikator = 1.645
        trall_tp = 0.15
        min_order_amount = 6
        max_order_amount = 3 * min_order_amount
        take_profit = 0.7
        max_take_profit = 5
        sl_take_ptofit = 0.1
        take_profit = take_profit + sl_take_ptofit
        multiplikator = 1.05
        min_pure_profit = 0.125  # мин прибыль ордера под которую будет расчитываться динамический ТП = 0,25%

        max_order_qty = 20

        min_working_time_of_grid = 86400
        sleep_time = 120
        time_to_update_order_status = 5

    elif ticket == "DOGEUSDT":
        grid_step = 0.25
        grid_multiplikator = 1.765
        trall_tp = 0.15
        min_order_amount = 6
        max_order_amount = 3 * min_order_amount
        take_profit = 1.5
        max_take_profit = 5
        sl_take_ptofit = 0.1
        take_profit = take_profit + sl_take_ptofit
        multiplikator = 1.05
        min_pure_profit = 0.125  # мин прибыль ордера под которую будет расчитываться динамический ТП = 0,25%


        max_order_qty = 20

        min_working_time_of_grid = 86400
        sleep_time = 120
        time_to_update_order_status = 5

    elif ticket == "ETHBTC":
        # print(f"Работаем по стандартной стратегии")
        grid_step = 0.5  # Шаг сетки - процент на который должна упасть цена для запуска входа в новый ордер
        grid_multiplikator = 1.2  # мультапликатор сетки
        trall_tp = 0.1  # Тралл TP 1% ТРАЛЛ ВХОДА. Это процент на которую должна поднятся цена после достижения уровня grid_step, для выставления лимитного ордера на вход в первый ордер сетки

        # min_order_amount = float(user_settings["symbol_list"][0][ticket]["user_minOrderAmt"])  # начальный ордер 10 баксов
        # if min_order_amount < 10:
        min_order_amount = 0.0002
        max_order_amount = 3 * min_order_amount
        take_profit = 0.7  # тейк профит 1%
        max_take_profit = 5  # максимальный тейк профит, если достигаем этого уровня, то закрываем сделку
        sl_take_ptofit = 0.1  # если потеряем sl_take_ptofit тейкпрофита, то выходим
        take_profit = take_profit + sl_take_ptofit
        multiplikator = 1.05
        min_pure_profit = 0.125  # мин прибыль ордера под которую будет расчитываться динамический ТП = 0,25%


        max_order_qty = 20

        min_working_time_of_grid = 86400  # время после которого мы готовы закрывать сетку по условию прибыль =2х от убытков
        sleep_time = 120
        time_to_update_order_status = 5  # обновляем статус ордеров через каждые time_to_update_order_status секунд

    elif ticket == "ARBUSDT":
        # print(f"Работаем по стандартной стратегии")
        grid_step = 0.3  # Шаг сетки - процент на который должна упасть цена для запуска входа в новый ордер
        grid_multiplikator = 1.71  # мультапликатор сетки
        trall_tp = 0.15  # Тралл TP 1% ТРАЛЛ ВХОДА. Это процент на которую должна поднятся цена после достижения уровня grid_step, для выставления лимитного ордера на вход в первый ордер сетки

        # min_order_amount = float(user_settings["symbol_list"][0][ticket]["user_minOrderAmt"])  # начальный ордер 10 баксов
        # if min_order_amount < 10:
        min_order_amount = 6
        max_order_amount = 3 * min_order_amount
        take_profit = 0.6  # тейк профит 1%
        max_take_profit = 5  # максимальный тейк профит, если достигаем этого уровня, то закрываем сделку
        sl_take_ptofit = 0.05  # если потеряем sl_take_ptofit тейкпрофита, то выходим
        take_profit = take_profit + sl_take_ptofit
        multiplikator = 1.05
        min_pure_profit = 0.125  # мин прибыль ордера под которую будет расчитываться динамический ТП = 0,25%

        max_order_qty = 20

        min_working_time_of_grid = 86400  # время после которого мы готовы закрывать сетку по условию прибыль =2х от убытков
        sleep_time = 120
        time_to_update_order_status = 5  # обновляем статус ордеров через каждые time_to_update_order_status секунд

    elif ticket == "MNTUSDT":
        # print(f"Работаем по стандартной стратегии")
        grid_step = 0.2  # Шаг сетки - процент на который должна упасть цена для запуска входа в новый ордер
        grid_multiplikator = 1.81  # мультапликатор сетки
        trall_tp = 0.15  # Тралл TP 1% ТРАЛЛ ВХОДА. Это процент на которую должна поднятся цена после достижения уровня grid_step, для выставления лимитного ордера на вход в первый ордер сетки

        # min_order_amount = float(user_settings["symbol_list"][0][ticket]["user_minOrderAmt"])  # начальный ордер 10 баксов
        # if min_order_amount < 10:
        min_order_amount = 6
        max_order_amount = 3 * min_order_amount
        take_profit = 0.6  # тейк профит 1%
        max_take_profit = 5  # максимальный тейк профит, если достигаем этого уровня, то закрываем сделку
        sl_take_ptofit = 0.05  # если потеряем sl_take_ptofit тейкпрофита, то выходим
        take_profit = take_profit + sl_take_ptofit
        multiplikator = 1.05
        min_pure_profit = 0.125  # мин прибыль ордера под которую будет расчитываться динамический ТП = 0,25%

        max_order_qty = 20

        min_working_time_of_grid = 86400  # время после которого мы готовы закрывать сетку по условию прибыль =2х от убытков
        sleep_time = 120
        time_to_update_order_status = 5  # обновляем статус ордеров через каждые time_to_update_order_status секунд


    elif ticket == "AVAXUSDT":
        # print(f"Работаем по стандартной стратегии")
        grid_step = 0.35  # Шаг сетки - процент на который должна упасть цена для запуска входа в новый ордер
        grid_multiplikator = 1.67  # мультапликатор сетки
        trall_tp = 0.15  # Тралл TP 1% ТРАЛЛ ВХОДА. Это процент на которую должна поднятся цена после достижения уровня grid_step, для выставления лимитного ордера на вход в первый ордер сетки

        # min_order_amount = float(user_settings["symbol_list"][0][ticket]["user_minOrderAmt"])  # начальный ордер 10 баксов
        # if min_order_amount < 10:
        min_order_amount = 6
        max_order_amount = 3 * min_order_amount
        take_profit = 0.6  # тейк профит 1%
        max_take_profit = 5  # максимальный тейк профит, если достигаем этого уровня, то закрываем сделку
        sl_take_ptofit = 0.05  # если потеряем sl_take_ptofit тейкпрофита, то выходим
        take_profit = take_profit + sl_take_ptofit
        multiplikator = 1.05
        min_pure_profit = 0.125  # мин прибыль ордера под которую будет расчитываться динамический ТП = 0,25%


        max_order_qty = 20

        min_working_time_of_grid = 86400  # время после которого мы готовы закрывать сетку по условию прибыль =2х от убытков
        sleep_time = 120
        time_to_update_order_status = 5  # обновляем статус ордеров через каждые time_to_update_order_status секунд

    else:  # стандартный набор исходных данных
        # print(f"Работаем по стандартной стратегии")
        grid_step = 0.5  # Шаг сетки - процент на который должна упасть цена для запуска входа в новый ордер
        grid_multiplikator = 1.2  # мультапликатор сетки
        trall_tp = 0.1  # Тралл TP 1% ТРАЛЛ ВХОДА. Это процент на которую должна поднятся цена после достижения уровня grid_step, для выставления лимитного ордера на вход в первый ордер сетки

        # min_order_amount = float(user_settings["symbol_list"][0][ticket]["user_minOrderAmt"])  # начальный ордер 10 баксов
        # if min_order_amount < 10:
        min_order_amount = 10
        max_order_amount = 3 * min_order_amount
        take_profit = 0.6  # тейк профит 1%
        max_take_profit = 5  # максимальный тейк профит, если достигаем этого уровня, то закрываем сделку
        sl_take_ptofit = 0.1  # если потеряем sl_take_ptofit тейкпрофита, то выходим
        take_profit = take_profit + sl_take_ptofit
        multiplikator = 1.05
        min_pure_profit = 0.125  # мин прибыль ордера под которую будет расчитываться динамический ТП = 0,25%

        max_order_qty = 20

        min_working_time_of_grid = 86400  # время после которого мы готовы закрывать сетку по условию прибыль =2х от убытков
        sleep_time = 120
        time_to_update_order_status = 5  # обновляем статус ордеров через каждые time_to_update_order_status секунд

    preset_dict = {}
    preset_dict[ticket] = {}
    preset_dict[ticket]["grid_step"] = grid_step
    preset_dict[ticket]["grid_multiplikator"] = grid_multiplikator
    preset_dict[ticket]["trall_tp"] = trall_tp
    preset_dict[ticket]["min_order_amount"] = min_order_amount
    preset_dict[ticket]["max_order_amount"] = max_order_amount
    preset_dict[ticket]["take_profit"] = take_profit
    preset_dict[ticket]["max_take_profit"] = max_take_profit
    preset_dict[ticket]["sl_take_ptofit"] = sl_take_ptofit
    preset_dict[ticket]["multiplikator"] = multiplikator
    preset_dict[ticket]["max_order_qty"] = max_order_qty
    preset_dict[ticket]["min_working_time_of_grid"] = min_working_time_of_grid
    preset_dict[ticket]["sleep_time"] = sleep_time
    preset_dict[ticket]["time_to_update_order_status"] = time_to_update_order_status
    preset_dict[ticket]["min_pure_profit"] = min_pure_profit

    preset_dict[ticket]["sushka_mode"] = False
    return preset_dict
##################################################
# ПРЕСЕТЫ для МОНЕТ. КОНЕЦ
##################################################


##################################################
# РАБОТА С СОКЕТАМИ. НАЧАЛО
##################################################
def socket_current_prices(symbol_list, stop_event,stop_event_socket, lock):
    api_key = ""
    api_secret = ""
    url = "wss://stream.bybit.com/v5/public/spot"
    # Генерация expires и signature:
    expires = int((datetime.datetime.now().timestamp() + 1) * 1000)
    message = f"GET/realtime{expires}"
    signature = hmac.new(api_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()

    # Настройка SSL:
    ca_certs_path = certifi.where()
    sslopt = {"cert_reqs": ssl.CERT_REQUIRED, "ca_certs": ca_certs_path}
    ws = None
    # Создание и запуск WebSocket:
    try:
        ws = websocket.create_connection(url, sslopt=sslopt)
        print("Connection opened")
        # Authentication:
        ws.send(json.dumps({"op": "auth", "args": [api_key, expires, signature]}))
        # Ping:
        ws.send(json.dumps({"req_id": "100001", "op": "ping"}))
        # Subscribe:
        subscribe_list = []
        for symbol in symbol_list:
            subscribe = "tickers."+symbol
            subscribe_list.append(subscribe)
        ws.send(json.dumps({"op": "subscribe", "args": subscribe_list})) # запрос к сокету ws.send(json.dumps({"op": "subscribe", "args": ["tickers.XRPUSDT", "tickers.ETHUSDT"]}))

        while stop_event.is_set() == False and stop_event_socket.is_set() == False: # работаем пока стоп события не активированы
            result = ws.recv()
            # print(f"Received: {result}")
            result = json.loads(result)
            # сохраним данные в словарь
            # try:
            if 'data' in result and result['data']:
                symbol = result['data']['symbol']
                ts = result['ts']
                current_price = result['data']['lastPrice']
                if current_price:
                    with lock:
                        # price_dict[symbol].append({"ts":float(f"{str(ts)[0:10]}.{str(ts)[-3:]}"),"current_price":float(current_price)})
                        price_dict[symbol].append({"ts":time.time(),"current_price":float(current_price)})

                        # print(f"Цена {symbol}: {current_price}, Размер списка: {len(price_dict[symbol])}")
                else:
                    print(f"'lastPrice' отсутствует в данных {message}")
            else:
                print(f"Нет данных в сообщении от сокета: {message}")
            # except Exception as ex:
            #     print(ex)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'ws' in locals() and ws:
            ws.close()
            print("Connection closed")
'''
# Функция для обработки сообщений WebSocket
def handle_message(message):
    try:
        if 'data' in message and message['data']:
            # print(message)
            ts = message['ts']
            current_price = message['data']['lastPrice']
            if current_price:
                with lock:
                    #price_list.append({"ts":ts,"current_price":current_price})
                    price_dict[symbol].append({"ts":float(f"{str(ts)[0:10]}.{str(ts)[-3:]}"),"current_price":float(current_price)})
                    #print(f"{price_dict=}")
                    #print({"ts":ts,"current_price":current_price})
                # print(f"Цена {symbol}: {current_price}, Размер списка: {len(price_list)}")
            else:
                print(f"'lastPrice' отсутствует в данных {message}")
        else:
            print(f"Нет данных в сообщении от сокета: {message}")
    except Exception as ex:
        print(ex)


def websocket_stream(symbol: str):
    """
    Запускает поток WebSocket и обрабатывает сообщения.
    """
    ws = None  # Инициализируем ws
    try:
        ws = WebSocket(testnet=False, channel_type="spot")
        ws.ticker_stream(symbol=symbol, callback=handle_message)

        print(f"Сокет {symbol} запущен")

        while not stop_event.is_set():
            time.sleep(1)  # Держать поток активным
    except Exception as e:
        print(f"Критическая ошибка WebSocket: {e}")
    finally:
        try:
            ws.close()  # Попытка закрыть вебсокет
        except Exception as e:
            print(f"Ошибка при закрытии вебсокета: {e}")
        print("WebSocket закрыт")


def run_websocket(symbol: str):
    """
    Обертка для запуска вебсокета с обработкой исключений и перезапуском.
    """
    attempt = 0
    max_attempt = 5
    #while not stop_event.is_set():
    while attempt < max_attempt:
        attempt+=1
        try:
            websocket_stream(symbol)
            time.sleep(5)  # Пауза перед перезапуском
        except Exception as e:
            print(f"Перезапуск WebSocket из-за ошибки: {e}")
            time.sleep(10)  # Больше пауза


# обертка для вебсокет для обратотки исключений
def run_websocket_safe(symbol: str):
    """
    Обертка для run_websocket, перехватывающая исключения и позволяющая основной программе работать дальше.
    """
    try:
        run_websocket(symbol)
    except Exception as e:
        print(f"Критическая ошибка в потоке WebSocket для {symbol}: {e}")
        traceback.print_exc()  # Выводим traceback для отладки.  Обязательно логируйте в реальном приложении.
'''
##################################################
# РАБОТА С СОКЕТАМИ. КОНЕЦ
##################################################

##################################################
# ГРАФИЧЕСКИЙ ИНТЕРФЕЙС. НАЧАЛО
##################################################
def update_base_user_settings_on_base(api_key_var, api_secret_var, chat_id_var, bot_name_var):
    with sq.connect("crypto_bull.db") as con:
        # обновим данные
        # update_order_data_json = json.dumps(update_order_data)  # Преобразуем словарь в строку JSON
        # изменяем данные в столбце
        try:
            cur = con.cursor()
            # проверим если ли запись в бд
            cur.execute("""
                            SELECT user_api_key, user_api_secret, user_chat_id,user_symbol_list
                            FROM actually_user_settings
                        """)
            result = cur.fetchone()
            #print(result)
            if result == None:  # значит поля с настройками еще нет, запишем новые настройки
                #print("значит поля с настройками еще нет, запишем данные в ДБ")
                cur.execute("""
                                            INSERT INTO actually_user_settings (user_api_key,user_api_secret,user_chat_id, user_bot_name)
                                            SELECT ?, ?, ?, ?

                                        """, (api_key_var, api_secret_var, chat_id_var, bot_name_var,))
                con.commit()  # сохраним изменения
            else:  # значит поле уже есть, обновим данные
                #print("значит поле уже есть, обновим данные")
                try:
                    print(f"новые данные для БД {api_key_var=},{api_secret_var=},{chat_id_var=}, {bot_name_var=}")
                    cur = con.cursor()
                    cur.execute("""
                                UPDATE actually_user_settings 
                                SET user_api_key = ?, user_api_secret = ?, user_chat_id = ?, user_bot_name = ?
                                WHERE user_api_key = ?
                            """, (api_key_var, api_secret_var, chat_id_var, bot_name_var, result[0]))  # Параметризованный запрос

                    con.commit()  # сохраним изменения
                except Exception as e:
                    print(f"Ошибка при обновлении данных: {e}")

        except Exception as e:
            print(f"Ошибка при обновлении данных: {e}")

        # # Проверяем результат
        # cur.execute("""
        #                             SELECT user_api_key, user_api_secret, user_chat_id
        #                             FROM actually_user_settings
        #                         """)
        # result = cur.fetchone()
        # if result:
        #     print(f"Обновленные данные: {result}")
        # else:
        #     print("Запись не найдена после обновления.")


def update_coin_user_settings_on_base(user_symbol_list, sushka_mode_list):
    with sq.connect("crypto_bull.db") as con:
        # обновим данные
        # update_order_data_json = json.dumps(update_order_data)  # Преобразуем словарь в строку JSON
        # изменяем данные в столбце
        try:
            cur = con.cursor()
            # проверим если ли запись в бд
            user_symbol_list = json.dumps(user_symbol_list)
            sushka_mode_list = json.dumps(sushka_mode_list)
            #print(f"{user_symbol_list=}")
            cur.execute("""
                            SELECT user_api_key, user_api_secret, user_chat_id,user_symbol_list,sushka_mode_list
                            FROM actually_user_settings
                        """)
            result = cur.fetchone()
            #print(f"{result[3]=}")

            if result[3] == None:  # значит поля с настройками еще нет, запишем новые настройки
                #print("значит поля с настройками еще нет, запишем данные в ДБ")
                #print(f"{user_symbol_list=},{type(user_symbol_list)}\n{sushka_mode_list=},{type(sushka_mode_list)}")
                cur = con.cursor()
                cur.execute("""
                                                UPDATE actually_user_settings 
                                                SET user_symbol_list = ?, sushka_mode_list = ?
                                                WHERE user_api_key = ?
                                            """,
                            (user_symbol_list, sushka_mode_list, result[0]))  # Параметризованный запрос

                con.commit()  # сохраним изменения
            else:  # значит поле уже есть, обновим данные
                cur.execute("""
                                            SELECT user_api_key, user_api_secret, user_chat_id,user_symbol_list,sushka_mode_list
                                            FROM actually_user_settings
                                        """)
                result = cur.fetchone()
                #print("значит поле уже есть, обновим данные")
                try:
                    # получим значение из sushka_mode_list базы
                    sushka_mode_list_from_base = result[4]
                    user_symbol_list_from_base = result[3]
                    sushka_mode_list = json.loads(sushka_mode_list)
                    sushka_mode_list_from_base = json.loads(sushka_mode_list_from_base)
                    user_symbol_list_from_base = json.loads(user_symbol_list_from_base)
                    #print(f"{sushka_mode_list_from_base=}", type(sushka_mode_list_from_base))
                    #print(f"{user_symbol_list_from_base=}", type(user_symbol_list_from_base))
                    #print(f"{sushka_mode_list=}", type(sushka_mode_list))
                    # если монеты уже была в sushka_mode_list_from_base, то возьмем значение сушки из базы
                    if sushka_mode_list_from_base != None:
                        sushka_mode_list_ready_to_update = {}
                        for key in sushka_mode_list:
                            if key in user_symbol_list:
                                if key in sushka_mode_list_from_base:
                                    sushka_mode_list_ready_to_update[key] = sushka_mode_list_from_base[key]
                                else:
                                    sushka_mode_list_ready_to_update[key] = sushka_mode_list[key]
                        sushka_mode_list = sushka_mode_list_ready_to_update
                    #print(f"{sushka_mode_list_ready_to_update=}")
                    # user_symbol_list = json.dumps(user_symbol_list)
                    sushka_mode_list = json.dumps(sushka_mode_list)
                    print(f"новые данные для БД {user_symbol_list=}\n{sushka_mode_list=}")
                    cur = con.cursor()
                    cur.execute("""
                                UPDATE actually_user_settings 
                                SET user_symbol_list = ?, sushka_mode_list = ?
                                WHERE user_api_key = ?
                            """, (user_symbol_list, sushka_mode_list, result[0]))  # Параметризованный запрос

                    con.commit()  # сохраним изменения
                except Exception as e:
                    print(f"Ошибка при обновлении данных: {e}")


        except Exception as e:
            print(f"Ошибка при обновлении данных: {e}")

        # # Проверяем результат
        # cur.execute("""
        #                             SELECT user_api_key, user_api_secret, user_chat_id,user_symbol_list,sushka_mode_list
        #                             FROM actually_user_settings
        #                         """)
        # result = cur.fetchone()
        # if result:
        #     print(f"Обновленные данные: {result}")
        # else:
        #     print("Запись не найдена после обновления.")


# начальные данные
# SETTINGS_FILE = "user_settings.json"
# MAX_SELECTED_COINS = 3
# ALLOWED_COINS = ["btcusdt", "xrpusdt", "ethusdt", "linkusdt", "tonusdt", "dotusdt"]



# sushka_flag = False


# Функция для запуска GUI в отдельном потоке
def run_gui():
    # Создание GUI
    root = tk.Tk()
    root.title("ESM Crypto Bull")
    root.geometry("700x470")

    # Создание стиля ttk
    style = ttk.Style()
    style.configure("TButton", padding=5, relief="flat")
    style.configure("Green.TButton", background="green")
    style.configure("Normal.TButton", background=root.cget("background"))

    # Создание Notebook (вкладок)
    notebook = ttk.Notebook(root)
    notebook.pack(expand=True, fill="both", padx=5, pady=5)

    # ====================== Вкладка 1: Основные настройки ======================
    settings_frame = ttk.Frame(notebook)
    notebook.add(settings_frame, text="Основные настройки")

    # проверяем есть ли готовый файл настроек в БД, если да то заполним ими поля
    with sq.connect("crypto_bull.db") as con:
        # обновим данные
        # update_order_data_json = json.dumps(update_order_data)  # Преобразуем словарь в строку JSON
        # изменяем данные в столбце
        cur = con.cursor()
        # проверим если ли запись в бд
        cur.execute("""
                            SELECT user_api_key, user_api_secret, user_chat_id, user_bot_name
                            FROM actually_user_settings
                        """)
        result = cur.fetchone()
        # print(result)
    if result != None:  # значит файл с настройками уже создан
        # if 1==2: # проверка если файл настроек в БД, возьмем данные для полей из БД
        #print(result)
        api_key_var = tk.StringVar(value=result[0])  # заполним поле данными из файла настроек
        api_secret_var = tk.StringVar(value=result[1])  # заполним поле данными из файла настроек
        chat_id_var = tk.StringVar(value=result[2])  # заполним поле данными из файла настроек
        bot_name_var = tk.StringVar(value=result[3])  # заполним поле данными из файла настроек
        # api_key_var = tk.StringVar(value=settings.get("user_api_key", ""))
        # api_secret_var = tk.StringVar(value=settings.get("user_api_secret", ""))
        # chat_id_var = tk.StringVar(value=settings.get("user_chat_id", ""))

    else:  # файла БД еще нет, заполним поля

        api_key_var = tk.StringVar(value="")  # заполним поле данными из файла настроек
        api_secret_var = tk.StringVar(value="")  # заполним поле данными из файла настроек
        chat_id_var = tk.StringVar(value="")
        bot_name_var = tk.StringVar(value="")

    # создаем поля для ввода данных
    ttk.Label(settings_frame, text="API Key:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
    api_key_entry = ttk.Entry(settings_frame, textvariable=api_key_var, width=30)
    api_key_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
    # api_key_entry.pack()

    ttk.Label(settings_frame, text="API Secret:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
    api_secret_entry = ttk.Entry(settings_frame, textvariable=api_secret_var, width=30, show="*")
    api_secret_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

    ttk.Label(settings_frame, text="Chat ID:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
    chat_id_entry = ttk.Entry(settings_frame, textvariable=chat_id_var)
    chat_id_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

    ttk.Label(settings_frame, text="Bot Name:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
    bot_name_entry = ttk.Entry(settings_frame, textvariable=bot_name_var)
    bot_name_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

    def on_closing():
        """Функция, вызываемая при попытке закрыть окно."""
        # global algorithm_running, root
        algorithm_running = True
        print("ОКНО ИНТЕРФЕЙСА ЗАКРЫТО")
        if algorithm_running:
            if messagebox.askokcancel("Выход", "Алгоритм выполняется. Прервать и выйти?"):
                stop_event.set()  # Устанавливаем флаг для остановки потока
                time.sleep(0.5)  # Небольшая задержка, чтобы алгоритм успел остановиться
                root.destroy()  # Закрываем окно
                # sys.exit(0)
            else:
                return  # Не закрываем окно
        else:
            root.destroy()
            # sys.exit(0)
        # print(f"{stop_event=}")


    # создадим функцию для сохранения основных настроек в БД
    def save_basic_settings():
        user_api_key = str(api_key_var.get())
        user_api_secret = api_secret_var.get()
        user_chat_id = chat_id_var.get()
        user_bot_name = bot_name_var.get()
        #print(f"{user_api_key=}")
        #print(f"{user_api_secret=}")
        #print(f"{user_chat_id=}")

        # save_settings_to_file()
        update_base_user_settings_on_base(api_key_var=user_api_key, api_secret_var=user_api_secret,
                                          chat_id_var=user_chat_id, bot_name_var=user_bot_name)
        messagebox.showinfo("Сохранено", "Основные настройки сохранены.")

    # создадим кнопку для запуска функции сохранения основных настроек в БД
    ttk.Button(settings_frame, text="Сохранить", command=save_basic_settings).grid(row=4, column=0, columnspan=2,
                                                                                   pady=10)

    # ====================== Вкладка 2: Основные настройки ======================

    # # Пример виджета на вкладке (замените на свои виджеты)
    # label1 = ttk.Label(coins_frame, text="Тут будут ваши настройки...")
    # label1.pack(padx=10, pady=10)

    # Список разрешенных монет
    # allowed_coins = ["btcusdt", "xrpusdt", "ethusdt", "linkusdt", "tonusdt", "dotusdt"]
    # max_selected_coins = 3  # Максимум можно выбрать 3 монеты


    # Добавляем user_coins в allowed_coins **ДО** создания кнопок!
    # ALLOWED_COINS.extend(user_coins)
    allowed_coins.extend(user_coins)

    # # Создаем главное окно
    # root = tk.Tk()
    # root.title("Выбор монет")
    # root.geometry("800x600")  # Размер окна

    # # Создаем вкладки
    # notebook = ttk.Notebook(root)
    # notebook.pack(expand=True, fill="both", padx=5, pady=5)  # Размещаем вкладки в окне

    # Вкладка для настроек монет
    coin_tab = ttk.Frame(notebook)
    notebook.add(coin_tab, text="Настройки монет")  # Добавляем вкладку и называем её

    # Создаем Canvas (холст) для размещения содержимого
    canvas = tk.Canvas(coin_tab)
    canvas.pack(side="left", fill="both", expand=True)

    # Создаем Scrollbar (полосу прокрутки)
    scrollbar = ttk.Scrollbar(coin_tab, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")

    # Конфигурируем Canvas для работы с Scrollbar
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    # Создаем фрейм внутри Canvas для размещения содержимого
    inner_frame = ttk.Frame(canvas)
    canvas.create_window((0, 0), window=inner_frame, anchor="nw")  # Размещаем фрейм в Canvas

    # Функция для прокрутки колесиком мыши
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # Привязываем колесико мыши к canvas
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # Стили для кнопок
    style = ttk.Style()
    style.configure("TButton", padding=5, relief="flat", width=10)  # Отступы, рамка, ширина
    style.configure("Green.TButton", background="green")  # Зеленый цвет для выбранных
    style.configure("Normal.TButton", background=root.cget("background"))  # Обычный цвет

    # Переменная для хранения состояния кнопок и настроек
    selected_coins = {}  # {coin_name: {"button": button_obj, "active":bool, "frame": frame_obj, "amount_var": amount_var, "percent_mode_var": percent_mode_var}}
    loaded_from_settings = False

    # Функция для получения названия монеты от пользователя
    def get_user_coin_name(button, coin):
        new_name = simpledialog.askstring("Название монеты", f"Введите название для {coin}:")
        if new_name:
            coin_buttons[new_name.lower()] = coin_buttons[coin]
            index = 0
            # print(f"{allowed_coins=}")
            # # TODO строчки ниже быть не должно поиидее
            # allowed_coins.extend(user_coins)
            #TODO проверка правильности введенного значения
            # получим список торгуемых символов на бирже
            # прочитаем пользовательские настройки из базы
            with sq.connect("crypto_bull.db") as con:
                try:
                    cur = con.cursor()
                    # проверим если ли запись в бд
                    cur.execute("""SELECT user_api_key, user_api_secret FROM actually_user_settings""")
                    result = cur.fetchone()
                except Exception as e:
                    print(f"Ошибка при чтении данных: {e}")
                user_api_key = result[0]
                user_api_secret = result[1]
            # Биржа ByBit
            # TODO раскоментировать строчку ниже, а строку еще ниже удалить
            session = HTTP(api_key=user_api_key, api_secret=user_api_secret)
            symbol_list = []  # список всех торгуемых тикетов
            symbol_info = session.get_instruments_info(category="spot")['result']['list']
            # print(symbol_info)
            for i in symbol_info:
                if i['status'] == 'Trading':
                    symbol_list.append(i['symbol'])

            if new_name.upper() not in symbol_list:
                messagebox.showerror("Ошибка", f"Недопустимое имя, пара должна торговаться на BYBIT.")
                return None
            if new_name.lower() in allowed_coins:
                messagebox.showerror("Ошибка", f"Такая пара уже есть в наборе.")
                return None
            if uid != "130602840" or uid != "41085914":
                if "usdt" not in new_name.lower():
                    messagebox.showerror("Ошибка", f"Можно выбирать только пары вида МОНЕТА/USDT.")
                    return None
            for i in allowed_coins:
                # print(i)
                # print(coin)
                if i == coin:
                    index_to_change = index
                index += 1
            allowed_coins[index_to_change] = new_name.lower()
            # allowed_coins.append(new_name.upper())

            return new_name.lower()
        return None  # Если пользователь отменил ввод

    # # Функция для создания кнопок монет
    # def create_coin_buttons():
    #     coin_buttons = {}  # Словарь для хранения кнопок
    #     row = 1  # Начинаем со второй строки, чтобы переключатель был выше кнопок
    #     for coin in allowed_coins:
    #         # Создаем кнопку
    #         button = ttk.Button(coin_tab, text=coin.upper(), command=lambda c=coin: toggle_coin(c),
    #                             style="Normal.TButton")  # Используем lambda для передачи аргумента
    #         button.grid(row=row, column=0, padx=5, pady=5, sticky="w")  # Размещаем кнопку в столбце (column=0)
    #         coin_buttons[coin] = button  # Добавляем кнопку в словарь
    #         row += 1  # Переходим к следующей строке
    #     return coin_buttons

    # Функция для создания кнопок монет
    def create_coin_buttons():
        coin_buttons = {}  # Словарь для хранения кнопок
        row = 1  # Начинаем со второй строки, чтобы переключатель был выше кнопок
        for coin in allowed_coins:
            # Создаем кнопку
            if coin.startswith(USER_COIN_PREFIX):
                button = ttk.Button(inner_frame, text=user_coin_names[coin],  # Используем название из словаря
                                    command=lambda c=coin: customize_user_coin(c),
                                    style="Normal.TButton")
            else:
                button = ttk.Button(inner_frame, text=coin.upper(), command=lambda c=coin: toggle_coin(c),
                                    style="Normal.TButton")  # Используем lambda для передачи аргумента
            button.grid(row=row, column=0, padx=5, pady=5, sticky="w")  # Размещаем кнопку в столбце (column=0)
            coin_buttons[coin] = button  # Добавляем кнопку в словарь
            row += 1  # Переходим к следующей строке
        # print(f"{coin_buttons=}")
        return coin_buttons

    # Функция для настройки "user coin" (получить название и активировать)
    def customize_user_coin(coin):
        button = coin_buttons[coin]
        new_coin_name = get_user_coin_name(button, coin)  # Получаем название от пользователя
        if new_coin_name:
            user_coin_names[coin] = new_coin_name  # Сохраняем новое название в словаре
            button.config(text=new_coin_name)  # Обновляем текст кнопки
            button.config(command=lambda c=new_coin_name: toggle_coin(c))  # меняем команду кнопки
            toggle_coin(new_coin_name)  # Активируем монету
        print(f"{user_coin_names=}")

    # Функция для переключения состояния монеты (выбрать/убрать выбор)
    def toggle_coin(coin):
        if coin in selected_coins and selected_coins[coin]["active"]:  # Если монета уже выбрана
            deactivate_coin(coin)  # Убираем выбор
        elif len(selected_coins) < max_selected_coins:  # Если можно выбрать еще монеты
            activate_coin(coin)  # Выбираем монету
        else:
            messagebox.showinfo("Информация",
                                f"Можно выбрать не более {max_selected_coins} монет.")  # Выводим сообщение об ограничении

    # Функция для активации монеты (отображение полей настроек)
    def activate_coin(coin):
        button = coin_buttons[coin]
        button.configure(style="Green.TButton")  # Меняем цвет кнопки

        amount_var = tk.StringVar()
        percent_mode_var = tk.BooleanVar(value=False)

        selected_coins[coin] = {"active": True, "button": button, "amount_var": amount_var,
                                "percent_mode_var": percent_mode_var}
        create_manual_settings(coin)  # Создаем фрейм настроек
        # button.config(state="normal")

    # Функция для деактивации монеты (скрытие полей настроек)
    def deactivate_coin(coin):
        button = coin_buttons[coin]
        button.configure(style="Normal.TButton")  # Возвращаем обычный цвет кнопки
        # button.config(state="normal")  # Делаем кнопку активной

        if coin in selected_coins:
            if "frame" in selected_coins[coin]:
                frame = selected_coins[coin]["frame"]  # Получаем фрейм
                frame.destroy()
            del selected_coins[coin]  # Удаляем запись о монете

    # def create_manual_settings(coin): # поля ввода рисуются блоком
    #     """Создает элементы управления для ручной настройки"""
    #     button = coin_buttons[coin]
    #     amount_var = selected_coins[coin]["amount_var"]
    #     percent_mode_var = selected_coins[coin]["percent_mode_var"]
    #     amount_label_text = tk.StringVar(value="Min order amount:")
    #     recommended_balance_label_visible = tk.BooleanVar(value=True)  # Добавлено
    #
    #     # Вычисляем номер ряда, где будет размещен фрейм с настройками
    #     row_num = allowed_coins.index(coin) + 1  # Ряд соответствует индексу монеты в списке
    #
    #     # Создаем фрейм для настроек конкретной монеты, чтобы красиво разместить
    #     frame = ttk.Frame(inner_frame, padding="1 1 1 1")  # добавляем отступы внутри фрейма
    #     frame.grid(row=row_num, column=1, padx=0, pady=0, sticky="w")  # Размещаем правее кнопки (column=1)
    #
    #     # Label для ввода суммы
    #     amount_label = ttk.Label(frame, textvariable=amount_label_text)  # Используем textvariable
    #     amount_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    #
    #     # Поле ввода суммы
    #     amount_entry = ttk.Entry(frame, textvariable=amount_var, width=10)
    #     amount_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
    #
    #     # Label для отображения рекомендованного депозита
    #     recommended_balance_label = ttk.Label(frame, text="Рекомендованный депозит: ")
    #     recommended_balance_label.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")
    #
    #     # Checkbutton для выбора режима "Процент от депозита"
    #     percent_toggle_button = ttk.Checkbutton(frame, text="Percent from deposit", variable=percent_mode_var,
    #                                             command=lambda c=coin: toggle_percent_mode(c, percent_mode_var,
    #                                                                                        amount_label_text, c,
    #                                                                                        recommended_balance_label,
    #                                                                                        recommended_balance_label_visible))  # Передаем c и виджет
    #     percent_toggle_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="w")
    #
    #     # Сохраняем информацию о виджетах и состоянии монеты
    #     selected_coins[coin]["frame"] = frame
    #     selected_coins[coin]["recommended_balance_label"] = recommended_balance_label
    #     selected_coins[coin]["amount_label_text"] = amount_label_text
    #     selected_coins[coin]["amount_entry"] = amount_entry
    #     selected_coins[coin]["percent_toggle_button"] = percent_toggle_button
    #
    #     # Привязываем событие изменения текста в поле ввода
    #     amount_var.trace("w", lambda name, index, mode, c=coin: update_recommended_balance(c))
    #
    #     update_recommended_balance(coin)  # Сразу обновляем расчет

    def create_manual_settings(coin):
        """Создает элементы управления для ручной настройки"""
        button = coin_buttons[coin]
        amount_var = selected_coins[coin]["amount_var"]
        percent_mode_var = selected_coins[coin]["percent_mode_var"]
        amount_label_text = tk.StringVar(value="Min order amount:")
        recommended_balance_label_visible = tk.BooleanVar(value=True)  # Добавлено

        # Вычисляем номер ряда, где будет размещен фрейм с настройками
        row_num = allowed_coins.index(coin) + 1  # Ряд соответствует индексу монеты в списке

        # Создаем фрейм для настроек конкретной монеты
        frame = ttk.Frame(inner_frame, padding="1 1 1 1")  # добавляем отступы внутри фрейма
        frame.grid(row=row_num, column=2, padx=10, pady=5, sticky="w")  # Размещаем правее кнопки

        # Label для ввода суммы
        amount_label = ttk.Label(frame, textvariable=amount_label_text)  # Используем textvariable
        amount_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Поле ввода суммы
        amount_entry = ttk.Entry(frame, textvariable=amount_var, width=10)
        amount_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Label для отображения рекомендованного депозита
        recommended_balance_label = ttk.Label(frame, text="Рекомендованный депозит: ")
        recommended_balance_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # Checkbutton для выбора режима "Процент от депозита"
        percent_toggle_button = ttk.Checkbutton(frame, text="Percent from deposit", variable=percent_mode_var,
                                                command=lambda c=coin: toggle_percent_mode(c, percent_mode_var,
                                                                                           amount_label_text, c,
                                                                                           recommended_balance_label,
                                                                                           recommended_balance_label_visible))  # Передаем c и виджет
        percent_toggle_button.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # Сохраняем информацию о виджетах и состоянии монеты
        selected_coins[coin]["frame"] = frame
        selected_coins[coin]["recommended_balance_label"] = recommended_balance_label
        selected_coins[coin]["amount_label_text"] = amount_label_text
        selected_coins[coin]["amount_entry"] = amount_entry
        selected_coins[coin]["percent_toggle_button"] = percent_toggle_button

        # Привязываем событие изменения текста в поле ввода
        amount_var.trace("w", lambda name, index, mode, c=coin: update_recommended_balance(c))

        update_recommended_balance(coin)  # Сразу обновляем расчет

    # Функция для переключения режима "Процент от депозита"
    def toggle_percent_mode(coin, percent_mode_var, amount_label_text, c, recommended_balance_label,
                            recommended_balance_label_visible):  # Принимаем coin и виджет
        if percent_mode_var.get():
            amount_label_text.set("Percent from deposit:")  # Меняем текст
            recommended_balance_label.grid_remove()  # Скрываем надпись
        else:
            amount_label_text.set("Min order amount:")  # Меняем текст
            recommended_balance_label.grid()  # Показываем надпись

        update_recommended_balance(coin)  # Пересчитываем депозит

    # Функция для обновления рекомендованного депозита
    def update_recommended_balance(coin):
        if coin in selected_coins:
            try:
                amount = float(selected_coins[coin]["amount_var"].get())
            except ValueError:
                amount = 0.0  # Если не введено число, используем 0
            recommended_balance = 20 * amount # на 10 ордеров
            recommended_balance = 33 * amount # на 20 ордеров

            selected_coins[coin]["recommended_balance_label"].config(
                text=f"Рекомендованный депозит: {recommended_balance:.2f}")  # Форматируем число

    # Функция для сохранения настроек в JSON файл
    # def save_settings():
    #     settings = {}
    #     sushka_mode_list = {}
    #     for coin, data in selected_coins.items():
    #         if data["active"]:  # Сохраняем только активные монеты
    #             amount_var = selected_coins[coin]["amount_var"]
    #             percent_mode_var = selected_coins[coin]["percent_mode_var"]
    #             settings[coin] = {
    #                 "amount": amount_var.get(),
    #                 "percent_mode": percent_mode_var.get()
    #             }
    #             sushka_mode_list[coin] = False
    #     print(f"{sushka_mode_list=}")
    #     user_symbol_list = settings
    #     update_coin_user_settings_on_base(user_symbol_list, sushka_mode_list)
    #     # with open(settings_file, "w") as f:  # Открываем файл для записи
    #     #     json.dump(settings, f, indent=4)  # Записываем данные в файл в формате JSON
    #     messagebox.showinfo("Информация", "Настройки сохранены.")  # Показываем сообщение
    #     load_settings()  # После сохранения обновляем состояние кнопок и полей
    def save_settings():
        settings = {}
        sushka_mode_list = {}
        for coin, data in selected_coins.items():
            if data["active"]:  # Сохраняем только активные монеты
                # print(coin)
                amount_var = selected_coins[coin]["amount_var"]
                percent_mode_var = selected_coins[coin]["percent_mode_var"]
                if coin in user_coin_names.values():
                    for usercoin in user_coin_names.keys():
                        if user_coin_names[usercoin] == coin:
                            user_coin_start_name = usercoin
                    print("USER COIN FINDED")
                    settings[coin] = {
                        "amount": amount_var.get(),
                        "percent_mode": percent_mode_var.get(),
                        "user_coin_start_name": user_coin_start_name
                    }
                else: # монета из персетов
                    settings[coin] = {
                        "amount": amount_var.get(),
                        "percent_mode": percent_mode_var.get()
                    }
                # #  # Проверка, является ли монета пользовательской
                # if coin.startswith(USER_COIN_PREFIX):
                #     print(f"{coin=}")
                #     user_coin_name = user_coin_names[coin]  # Получаем название пользовательской монеты
                #     settings[user_coin_name] = {  # Сохраняем с новым именем
                #         "amount": amount_var.get(),
                #         "percent_mode": percent_mode_var.get(),
                #         "user_coin_start_name": coin
                #     }
                # else:
                #     settings[coin] = {
                #         "amount": amount_var.get(),
                #         "percent_mode": percent_mode_var.get()
                #     }
                sushka_mode_list[coin] = False
        # print(f"{sushka_mode_list=}")
        # print(f"{selected_coins=}")
        # print(f"{settings=}")
        # TODO выполним проверки, что в selected_coins введены правильные данные
        is_all_inputs_int = True  # первая проверка - все введенные данные должны быть целыми числами
        is_all_inputs_digit = True  # проверка - все что ввели должно быть числом
        is_all_checkboxes_on_or_off = True  # проверка - все чекбоксы должны быть либо включены либо выключены
        is_summ_percent_equal_100 = True
        is_equity_enought_to_percent_mode = True
        is_equity_enought_to_handle_mode = True
        is_all_checkboxes_on_or_off_list = []
        percent_mode_counter = 0
        for key in selected_coins:
            try:
                amount_var = float(selected_coins[key]["amount_var"].get())
            except Exception as ex:
                is_all_inputs_digit = False
                messagebox.showerror("Ошибка", f"Введенные данные должны быть числами.")
            # if is_all_inputs_digit == True:
            #     # print(amount_var)
            #     if amount_var != int(amount_var):  # если число не целое
            #         is_all_inputs_int = False

            percent_mode_var = selected_coins[key]["percent_mode_var"].get()
            # print(percent_mode_var)
            if percent_mode_var == True:
                is_all_checkboxes_on_or_off_list.append("1")
            else:
                is_all_checkboxes_on_or_off_list.append("0")
            # if is_all_inputs_int == True:
            if is_all_inputs_digit == True:
                try:
                    percent_mode_counter += amount_var
                except Exception as ex:
                    print(ex)

        # if is_all_inputs_int == False:
        #     messagebox.showerror("Ошибка", f"Введенные данные должны быть целыми числами.")
        if len(set(is_all_checkboxes_on_or_off_list)) != 1:
            is_all_checkboxes_on_or_off = False
            messagebox.showerror("Ошибка", f"Чекбоксы должны быть либо включены либо выключены.")
        # else:
        #     print("все чекбоксы ОДИНАКОВЫЕ!!!")
        # if is_all_inputs_int == True:
        if is_all_inputs_digit == True:
            # проверка - если работаем по проценту от депа, то сумма всех введенных данных должна быть равна 100
            if percent_mode_var == True:
                if percent_mode_counter != 100:
                    is_summ_percent_equal_100 = False
                    messagebox.showerror("Ошибка",
                                         f"Работаем по проценту от депозита, сумма всех введнных значений должна быть равна 100.")

            # TODO проверка, если работаем по проценту, расчитаем минимальные ордера
            # прочитаем пользовательские настройки из базы
            with sq.connect("crypto_bull.db") as con:
                try:
                    cur = con.cursor()
                    # проверим если ли запись в бд
                    cur.execute("""SELECT user_api_key, user_api_secret FROM actually_user_settings""")
                    result = cur.fetchone()
                except Exception as e:
                    print(f"Ошибка при чтении данных: {e}")
                user_api_key = result[0]
                user_api_secret = result[1]
            # Биржа ByBit
            # TODO раскоментировать строчку ниже, а строку еще ниже удалить
            session = HTTP(api_key=user_api_key, api_secret=user_api_secret)
            totalEquity = float(session.get_wallet_balance(accountType="UNIFIED", )['result']['list'][0]['totalEquity'])
            if uid == "130602840":
                totalEquity = 10000
            # print(totalEquity)

            if percent_mode_var == True:
                for key in selected_coins:
                    amount_var = float(selected_coins[key]["amount_var"].get())
                    # определим минимальный возможный ордер по монете
                    instruments_info = session.get_instruments_info(category="spot", symbol=key.upper())
                    minOrderAmt = float(
                        instruments_info['result']['list'][0]['lotSizeFilter']['minOrderAmt'])  # минимальный ордер в баксах
                    # minOrderAmt = math.ceil(minOrderAmt * 1.15)  # добавим 15% и округлим в большую сторону, чтобы не получить ордер на продажу с недостаточным количеством монет
                    minOrderAmt = 2 * minOrderAmt  # за минимально возможный ордер возьмем 2х от минимальной закупки монеты на бирже
                    if key.upper() == "BTCUSDT":
                        minOrderAmt = 3 * minOrderAmt
                    # print(f"{minOrderAmt=}")
                    # расчитаем сумму которую пользователь выделил на монету и расчетный мин ордер
                    deposite_to_coin = totalEquity * amount_var / 100
                    # deposite_to_coin = 200
                    max_order_qty = coin_strategy(key.upper())[key.upper()]["max_order_qty"]
                    # print(f"{max_order_qty=}")
                    counted_min_order_amount = deposite_to_coin / max_order_qty / 2
                    # print(f"{deposite_to_coin=}")
                    # print(f"{counted_min_order_amount=}")
                    if counted_min_order_amount < minOrderAmt:
                        is_equity_enought_to_percent_mode = False
                        # messagebox.showerror("Ошибка",
                        #                      f"Недостаточно средств для работы с {key.upper()}, минимальный ордер для работы {minOrderAmt}usdt, расчитанный минимальный ордер по вашим данным {round(counted_min_order_amount, 2)}usdt. Выделите на монету больший процент депозита/уменьшите количество монет/пополните баланс.")
                        messagebox.showerror("Ошибка",
                                             f"Ошибка!\nМинимальный ордер по торговому символу {key.upper()} ниже минимального.\nПополните баланс счета или увеличте процент от депозита.")

            # если работаем в ручном режиме, провермим что указанный ордер не меньше минимального и сумма всех рекомендуемых депозитов не больше эквити
        # if is_all_inputs_int == True:
        if is_all_inputs_digit == True:
            handle_mode_counter = 0
            if percent_mode_var == False:
                for key in selected_coins:
                    amount_var = float(selected_coins[key]["amount_var"].get())
                    max_order_qty = coin_strategy(key.upper())[key.upper()]["max_order_qty"]
                    minOrderAmt = coin_strategy(key.upper())[key.upper()]["min_order_amount"]
                    recomended_deposite = amount_var * max_order_qty * 2
                    handle_mode_counter += recomended_deposite
                    if amount_var < minOrderAmt:
                        is_equity_enought_to_handle_mode = False
                        messagebox.showerror("Ошибка",
                                             f"Минимальный ордер меньше минимально допустимого. Укажите min order amount для {key.upper()} больше или равный {minOrderAmt}usdt")
            if handle_mode_counter > totalEquity:
                # is_equity_enought_to_handle_mode = False
                # messagebox.showerror("Ошибка",
                #                      f"Недостаточно средств для работы с выбранными монетами, минимальный депозит для работы {handle_mode_counter}usdt, эквити счета {round(totalEquity, 2)}usdt. Уменьшите минимальный ордер/уменьшите количество монет/пополните баланс.")
                messagebox.showerror("Ошибка",
                                     f"Внимание! Средств на счете меньше рекомендуемого депозита для работы.\nРекомендованный баланс {handle_mode_counter}usdt.\nТекущий баланс счета {round(totalEquity, 2)}usdt.")

        # сохраним данные если все проверки пройдены
        all_check_passed = False
        # if is_all_inputs_digit == True and is_all_inputs_int == True and is_all_checkboxes_on_or_off == True and is_summ_percent_equal_100 == True and is_equity_enought_to_percent_mode == True and is_equity_enought_to_handle_mode == True:
        if is_all_inputs_digit == True and is_all_checkboxes_on_or_off == True and is_summ_percent_equal_100 == True and is_equity_enought_to_percent_mode == True and is_equity_enought_to_handle_mode == True:

            all_check_passed = True

        if all_check_passed == True:
            user_symbol_list = settings
            update_coin_user_settings_on_base(user_symbol_list, sushka_mode_list)
            # with open(settings_file, "w") as f:  # Открываем файл для записи
            #     json.dump(settings, f, indent=4)  # Записываем данные в файл в формате JSON
            messagebox.showinfo("Информация", "Настройки сохранены.")  # Показываем сообщение
            load_settings()  # После сохранения обновляем состояние кнопок и полей

    # Функция для загрузки настроек из JSON-файла
    def load_settings():
        """Загружает настройки из JSON-файла."""
        global loaded_from_settings
        loaded_from_settings = True

        try:
            # if os.path.exists(settings_file):
            #     with open(settings_file, 'r') as f:
            #         settings = json.load(f)
            #

            with sq.connect("crypto_bull.db") as con:
                # обновим данные
                # update_order_data_json = json.dumps(update_order_data)  # Преобразуем словарь в строку JSON
                # изменяем данные в столбце
                try:
                    cur = con.cursor()
                    # проверим если ли запись в бд
                    cur.execute("""
                                    SELECT user_symbol_list
                                    FROM actually_user_settings
                                """)
                    result = cur.fetchone()
                    #print(result)
                    if result[0] != None:  # значит поля с настройками уже есть, загрузим данные
                        #print("ЗАГРУЗКА МОНЕТ С БАЗЫ")
                        #print(result[0])
                        data = result[0]
                        if data == None:
                            data = '{}'
                        settings = json.loads(data)
                        #print("значит поля с настройками монет уже есть, прочитаем настройки")

                        # Восстанавливаем названия пользовательских монет
                        # список монет, название которых нужно загрузить из базы
                        user_coin_to_load_name_list = []
                        user_coin_to_load_name_dict = {}
                        for key_coin in settings:
                            if "user_coin_start_name" in settings[key_coin]:
                                user_coin_to_load_name_list.append(settings[key_coin]["user_coin_start_name"])
                                user_coin_to_load_name_dict[settings[key_coin]["user_coin_start_name"]] = key_coin
                        # print(f"{user_coin_to_load_name_list=}")
                        # print(f"{user_coin_to_load_name_dict=}")
                        for coin in user_coin_to_load_name_list:
                            # Получаем кнопку
                            saved_coin_name = user_coin_to_load_name_dict[coin]
                            button = coin_buttons[coin]
                            if saved_coin_name:
                                #  # Обновляем название монеты
                                user_coin_names[coin] = saved_coin_name
                                #  # Обновляем текст кнопки
                                button.config(text=saved_coin_name)
                                #  # Обновляем команду для toggle_coin
                                button.config(command=lambda c=saved_coin_name: toggle_coin(c))
                            #обновим allowed_coins в соответствии с названиями пользовательских монет из базы
                            index = 0
                            index_to_change = ""
                            for i in allowed_coins:
                                if i == coin:
                                    index_to_change = index
                                index += 1
                            if index_to_change != "":
                                allowed_coins[index_to_change] = saved_coin_name.lower()
                                # обновим coin_buttons
                                coin_buttons[saved_coin_name.lower()] = coin_buttons[coin]
                                coin_buttons.pop(coin)
                        # print(f"{allowed_coins=}")
                        # print(f"{coin_buttons=}")
                        # Обновляем состояние кнопок и полей на основе настроек из файла
                        for coin in allowed_coins:
                            button = coin_buttons[coin]
                            # if coin in user_coin_to_load_name_dict:
                            #     coin = user_coin_to_load_name_dict[coin]
                            if coin in settings:
                                # Активируем монету, если она в файле
                                if coin not in selected_coins or not selected_coins[coin]["active"]:
                                    activate_coin(coin)

                                amount_var = selected_coins[coin]["amount_var"]
                                percent_mode_var = selected_coins[coin]["percent_mode_var"]

                                amount_var.set(settings[coin]["amount"])
                                percent_mode_var.set(settings[coin]["percent_mode"])

                                selected_coins[coin]["amount_entry"].config(state="normal")
                                selected_coins[coin]["percent_toggle_button"].config(state="disabled")

                                if settings[coin]["percent_mode"]:
                                    selected_coins[coin]["recommended_balance_label"].grid_remove()
                                    selected_coins[coin]["amount_label_text"].set("Percent from deposit:")
                                else:
                                    selected_coins[coin]["amount_label_text"].set("Min order amount:")

                                button.config(state="disabled")

                            else:
                                # Если монеты нет в файле, деактивируем и скрываем элементы управления
                                button.config(state="normal")
                                if coin in selected_coins:
                                    deactivate_coin(coin)

                        # check_max_selection() # Обновляем состояние кнопок
                        check_max_selection()
                except Exception as e:
                    print(f"Ошибка при обновлении данных: {e}")
        except FileNotFoundError:
            print("Файл настроек не найден.")
        except json.JSONDecodeError:
            print("Ошибка декодирования JSON.")
        except Exception as e:
            print(f"Произошла ошибка: {e}")

        loaded_from_settings = False  # Сбрасываем флаг

    # Функция для проверки максимального количества выбранных монет и блокировки/разблокировки кнопок
    def check_max_selection():
        selected_count = len(selected_coins)
        for coin, button in coin_buttons.items():
            if coin in selected_coins:
                button.config(state="disabled")
            elif selected_count < max_selected_coins:
                button.config(state="normal")
            else:
                button.config(state="normal")

    def periodic_update(user_symbol_list_start):
        """Периодическое обновление данных из файла."""
        user_symbol_list_current = None  # Инициализируем переменную
        # прочитаем текущее значение
        # получим начальное значение user_symbol_list_start
        try:
            with sq.connect("crypto_bull.db") as con:
                cur = con.cursor()
                # проверим если ли запись в бд
                cur.execute("""
                                    SELECT user_symbol_list
                                    FROM actually_user_settings
                                """)
                result = cur.fetchone()
                if result != None:  # значит поля с настройками уже есть, загрузим данные
                    data = result[0]
                    if data == None:
                        data = '{}'
                    user_symbol_list_current = json.loads(data)
        except Exception as ex:
            print(ex)
        if user_symbol_list_current != user_symbol_list_start:
            print("Пользовательские настройки изменились, обновим вкладку МОНЕТЫ")
            load_settings()
            user_symbol_list_start = user_symbol_list_current
        else:
            # print("Пользовательские настройки не изменились")
            asdasdasd=1
        root.after(5000, lambda: periodic_update(user_symbol_list_start))  # 10000 мс = 10 секунд

    # Создаем кнопки монет и размещаем их
    coin_buttons = create_coin_buttons()

    # Кнопка для сохранения настроек -  Используем grid()
    save_button = ttk.Button(inner_frame, text="Сохранить")
    # save_button.grid(row=len(allowed_coins) + 1, column=0, columnspan=2, pady=20, padx=20, sticky="ew")  # размещаем внизу
    save_button.grid(row=len(allowed_coins) + 1, column=0, columnspan=3, pady=20, padx=20,
                     sticky="ew")  # размещаем внизу
    save_button.configure(command=save_settings)  # подключаем команду сохранения

    # получим начальное значение user_symbol_list_start
    try:
        with sq.connect("crypto_bull.db") as con:
            cur = con.cursor()
            # проверим если ли запись в бд
            cur.execute("""
                            SELECT user_symbol_list
                            FROM actually_user_settings
                        """)
            result = cur.fetchone()
            if result != None:  # значит поля с настройками уже есть, загрузим данные
                data = result[0]
                if data == None:
                    data = '{}'
                user_symbol_list_start = json.loads(data)
            else:
                user_symbol_list_start = {}  # Инициализируем значение
    except Exception as ex:
        user_symbol_list_start = {}  # Инициализируем значение
    #print(f"{user_symbol_list_start=}")

    # Первичная загрузка
    load_settings()
    periodic_update(user_symbol_list_start)

    # ====================== Вкладка 3: Мониторинг ======================

    # Список разрешенных монет
    # allowed_coins = ["btcusdt", "xrpusdt", "ethusdt", "linkusdt", "tonusdt", "dotusdt"]


    # Функция для переключения режима "сушки"
    def toggle_shushka(coin):
        global shushka_mode
        shushka_mode[coin] = not shushka_mode[coin]
        if shushka_mode[coin]:
            button_text = "СУШКА (вкл)"
        else:
            button_text = "СУШКА (выкл)"
        shushka_buttons[coin].config(text=button_text)
        #print(f"{shushka_mode=}")
        save_shushka_mode_to_db(shushka_mode=shushka_mode)

    # Функция для создания элементов управления монет на вкладке "Мониторинг"
    def create_monitoring_elements(monitor_tab, shushka_mode):
        """Создает элементы управления монет на вкладке мониторинга."""
        global shushka_buttons

        shushka_buttons = {}  # Создаем новый словарь для кнопок "СУШКА"

        label_width = 10  # Устанавливаем фиксированную ширину для лейблов монет
        row_num = 1  # Начинаем со второй строки

        for coin in allowed_coins:
            if coin in shushka_mode:
                coin_frame = ttk.Frame(monitor_tab)
                coin_frame.grid(row=row_num, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

                coin_label = ttk.Label(coin_frame, text=f"{coin.upper()}:", width=label_width, anchor="w")
                coin_label.pack(side="left", padx=(0, 10))

                button_text = "СУШКА (вкл)" if shushka_mode.get(coin, False) else "СУШКА (выкл)"
                shushka_button = ttk.Button(coin_frame, text=button_text, command=lambda c=coin: toggle_shushka(c),
                                            width=15)
                shushka_button.pack(side="left", padx=(10, 0))
                shushka_buttons[coin] = shushka_button

                row_num += 1

    # Функция для обновления состояния кнопок на вкладке мониторинга
    def update_monitoring_tab(monitor_tab, shushka_mode):
        """Обновляет вкладку мониторинга."""

        # Удаляем все виджеты на вкладке мониторинга
        for widget in monitor_tab.winfo_children():
            widget.destroy()

        # Заново создаем элементы управления
        create_monitoring_elements(monitor_tab, shushka_mode)

        # Выводим сообщение
        # print("Вкладка мониторинга обновлена.")

    # Функция для получения начального состояния shushka_mode из базы данных
    def get_initial_shushka_mode(db_name="crypto_bull.db"):
        conn = None
        try:
            conn = sq.connect(db_name)
            cur = conn.cursor()
            cur.execute("SELECT sushka_mode_list FROM actually_user_settings")
            result = cur.fetchone()

            if result:
                shushka_mode_str = result[0]
                if shushka_mode_str == None:
                    shushka_mode = {}
                else:
                    shushka_mode = json.loads(shushka_mode_str)
                return shushka_mode
            else:
                return {}

        except Exception as e:
            print(f"Ошибка при чтении sushka_mode_list из базы данных: {e}")
            return {}
        finally:
            if conn:
                conn.close()

    # Функция для сохранения shushka_mode в базу данных
    def save_shushka_mode_to_db(shushka_mode):
        conn = None
        try:
            conn = sq.connect("crypto_bull.db")
            cur = conn.cursor()
            shushka_mode_json = json.dumps(shushka_mode)
            cur.execute("SELECT COUNT(*) FROM actually_user_settings")
            count = cur.fetchone()[0]
            #print(f"{shushka_mode_json=}")
            if count > 0:
                cur.execute("UPDATE actually_user_settings SET sushka_mode_list = ? ", (shushka_mode_json,))
            else:
                cur.execute("INSERT INTO actually_user_settings (sushka_mode_list) VALUES (?)", (shushka_mode_json,))

            conn.commit()
            print("shushka_mode сохранен в базу данных.")

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Ошибка при сохранении shushka_mode в базу данных: {e}")
        finally:
            if conn:
                conn.close()

    # Функция для периодического обновления вкладки мониторинга
    def periodic_update_monitoring_tab(monitor_tab, root):
        global shushka_mode

        shushka_mode = get_initial_shushka_mode()
        update_monitoring_tab(monitor_tab, shushka_mode)
        root.after(10000, lambda: periodic_update_monitoring_tab(monitor_tab, root))

    # Вкладка "сушка"
    monitor_tab = ttk.Frame(notebook)
    notebook.add(monitor_tab, text="Сушка")

    # Инициализируем shushka_mode и создаем элементы управления
    shushka_mode = get_initial_shushka_mode()
    create_monitoring_elements(monitor_tab, shushka_mode)

    # Запускаем периодическое обновление
    periodic_update_monitoring_tab(monitor_tab, root)


    # --------------- 4я вкладка МОНИТОРИНГ ------------------------------#
    # Функция для обновления содержимого терминала
    def update_terminal(terminal, lock, messages, root):
        """Обновляет содержимое терминала, отображая только последние 10000 сообщений (символов?)."""
        max_messages = 10000  # Максимальное количество отображаемых сообщений

        with lock:
            new_messages = messages[:]  # Копируем сообщения
            messages.clear()  # Очищаем список сообщений

        # Получаем текущее содержимое терминала
        terminal.configure(state='normal')
        current_content = terminal.get("1.0", tk.END)
        terminal.configure(state='disabled')

        all_messages = current_content.strip().split('\n') # Преобразуем в список
        # Добавляем новые сообщения
        with lock:
            all_messages.extend(new_messages)

        # Ограничиваем количество сообщений
        if len(all_messages) > max_messages:
            all_messages = all_messages[-max_messages:]  # Берем только последние max_messages

        # Формируем текст для вставки
        new_text = '\n'.join(all_messages) + '\n'

        # Обновляем терминал (без очистки)
        terminal.configure(state='normal')
        terminal.delete("1.0", tk.END)  # Очищаем терминал
        terminal.insert(tk.END, new_text)  # Вставляем новый текст
        terminal.see(tk.END)  # Прокручиваем в конец
        terminal.configure(state='disabled')  # Запрещаем редактирование
        root.after(10000, lambda: update_terminal(terminal, lock, messages, root))  # Планируем повторный вызов

    # Вкладка "Терминал"
    terminal_tab = ttk.Frame(notebook)
    notebook.add(terminal_tab, text="Терминал")

    terminal = scrolledtext.ScrolledText(terminal_tab, wrap=tk.WORD, state='disabled')
    terminal.pack(expand=True, fill="both", padx=10, pady=10)

    root.after(0, lambda: update_terminal(terminal, lock, messages, root))  # Запускаем обновление терминала

    # функция для иконки
    def set_app_icon(root):
        """Устанавливает иконку приложения."""
        icon_path = "esm.ico"
        try:
            # Для Windows, попробуем использовать .ico файл
            if os.name == 'nt' and icon_path.endswith('.ico'):
                root.iconbitmap(icon_path)
            else:
                # Для других платформ используем Pillow для обработки .png
                img = Image.open(icon_path)
                photo = ImageTk.PhotoImage(img)
                root.iconphoto(False, photo)
        except Exception as e:
            print(f"Ошибка при установке иконки: {e}")

    # устанавливаем иконку
    set_app_icon(root)

    # Настройка закрытия окна:
    root.protocol("WM_DELETE_WINDOW", on_closing)  # Перехватываем событие закрытия

    # # отрисовка и запуск интерфейса (Обязательно в конце)
    root.mainloop()  # Запускаем главный цикл tkinter


##################################################
# ГРАФИЧЕСКИЙ ИНТЕРФЕЙС. КОНЕЦ
##################################################


##################################################
# РАБОТА С БАЗОЙ ДАННЫХ. НАЧАЛО
##################################################
#функция для создания структуры базы данных с таблицами
def create_database():
    with sq.connect("crypto_bull.db") as con:
        timer_1 = datetime.datetime.now().timestamp()
        cur = con.cursor()

        # создаем таблицу для текущих сеток open_grid
        cur.execute("""
            CREATE TABLE IF NOT EXISTS open_grid (
                first_order_in_grid TEXT,
                symbol TEXT,
                open_grid_data TEXT
            )
        """)

        # создаем таблицу для closed_grid
        cur.execute("""
                CREATE TABLE IF NOT EXISTS closed_grid (
                    first_order_in_grid TEXT,
                    symbol TEXT,
                    open_grid_data TEXT
                )
            """)

        # создаем таблицу для completed_grid
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS completed_grid (
                        first_order_in_grid TEXT,
                        symbol TEXT,
                        open_grid_data TEXT
                    )
                """)

        # создаем таблицу для актуальных пользовательских настроек actually_user_settings
        cur.execute("""
                            CREATE TABLE IF NOT EXISTS actually_user_settings (
                                user_api_key  TEXT,
                                user_api_secret TEXT,
                                user_chat_id TEXT,
                                user_symbol_list TEXT,
                                sushka_mode_list TEXT

                            )
                        """)
        # добавим новый столбец с названием бота в таблицу
        try:
            cur.execute(f"""
                    ALTER TABLE actually_user_settings 
                    ADD COLUMN user_bot_name TEXT
                """)
            print(f"Столбец user_bot_name успешно добавлен в таблицу actually_user_settings.")
        except sq.OperationalError as e:
            print(f"Ошибка при добавлении столбца: {e}")


        con.commit()  # сохраним изменения

        # Ограничиваем количество строк в completed_grid
        cur = con.cursor()
        cur.execute("""
                    DELETE FROM completed_grid
                    WHERE rowid NOT IN (SELECT rowid FROM completed_grid ORDER BY rowid DESC LIMIT 1500)
                """)
        con.commit()

        print("Подключение к базе дынных выполнено.")
# Функция запись новой сетки в в таблицу open_grid
def add_new_grid_to_base(first_order_in_grid,symbol,orders_data):
    with sq.connect("crypto_bull.db") as con:

        # запись данных о новой сетке
        orders_data_json = json.dumps(orders_data) # Преобразуем словарь в строку JSON
        cur = con.cursor()
        # запись без проверки, если запись с таким first_order_in_grid уже существует
        # cur.execute("""
        #         INSERT INTO open_grid (first_order_in_grid, symbol, open_grid_data)
        #         VALUES (?, ?, ?)
        #     """, (first_order_in_grid, symbol, orders_data_json))  # Добавлен symbol

        try:
            cur.execute("""
                    INSERT INTO open_grid (first_order_in_grid, symbol, open_grid_data)
                    SELECT ?, ?, ?
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM open_grid
                        WHERE first_order_in_grid = ?
                    )
                """, (first_order_in_grid, symbol, orders_data_json,
                      first_order_in_grid))  # first_order_in_grid добавлен еще раз для WHERE NOT EXISTS
            con.commit()
            #print("Запись добавлена (если не существовала).")

        except sq.IntegrityError:  # Обработка ошибок, если столбец first_order_in_grid является UNIQUE
            print("Ошибка: Запись с таким first_order_in_grid уже существует (UNIQUE constraint violation).")

        except Exception as e:
            print(f"Произошла ошибка: {e}")

        con.commit()  # сохраним изменения

# функция прочесть данные из текущей сетки
def get_open_grid_orders_data(symbol):
    with sq.connect("crypto_bull.db") as con:
        cur = con.cursor()
        cur.execute("SELECT EXISTS(SELECT 1 FROM open_grid WHERE symbol = ?)", (symbol,))
        # Получаем результат запроса
        result = cur.fetchone()[0]  # если result = 0, то сетки с заданным тикетом нет в таблице open_grid, если 1, то есть
        if result == 1:
            # Получим данные найденного поля (файл сетки)
            cur.execute("SELECT open_grid_data FROM open_grid WHERE symbol = ?", (symbol,))
            data = cur.fetchone()[0]
    return data


# появился close ордер в сетке/изменилася статус во время контроля ордеров, обновим данные сетки
def update_open_grid_on_base(first_order_in_grid,update_order_data):
    with sq.connect("crypto_bull.db") as con:
        # обновим данные об открытой сетке
        #
        update_order_data_json = json.dumps(update_order_data)  # Преобразуем словарь в строку JSON
        # изменяем данные в столбце
        try:
            cur = con.cursor()
            cur.execute("""
                        UPDATE open_grid 
                        SET open_grid_data = ? 
                        WHERE first_order_in_grid = ?
                    """, (update_order_data_json, first_order_in_grid))  # Параметризованный запрос

            con.commit()  # сохраним изменения
        except Exception as ex:
            print(f"Ошибка при обновлении данных: {ex}")
            tb_str = traceback.format_exc()
            time_error = datetime.datetime.now()
            if admin_module == True:
                log_text = f"ОШИБКА В update_open_grid_on_base {time_error}\n{ex}\n{tb_str}\n"
                print(f"ОШИБКА В update_open_grid_on_base {time_error}\n{ex}\n{tb_str}\n")
                with open('Error_logger.txt', 'a+', encoding='utf-8-sig') as file:
                    try:
                        file.write(log_text)
                    finally:
                        file.close()
            else:
                log_text = f"ОШИБКА В update_open_grid_on_base {time_error}\n{ex}\n"
                with open('Error_logger.txt', 'a+', encoding='utf-8-sig') as file:
                    try:
                        file.write(log_text)
                    finally:
                        file.close()
                print(ex)

        # Проверяем результат
        cur.execute("SELECT open_grid_data FROM open_grid WHERE first_order_in_grid = ?", (first_order_in_grid,))
        result = cur.fetchone()
        # if result:
        #     print(f"Обновленные данные: {json.loads(result[0])}")
        # else:
        #     print("Запись не найдена после обновления.")
# сетка закрылась, переносим запись в closed_grid, а в open_grid удаляем
def transfer_grid_from_open_to_closed(first_order_in_grid):
    try:
        with sq.connect("crypto_bull.db") as con:
            cur = con.cursor()

            # Начинаем транзакцию
            cur.execute("BEGIN TRANSACTION")

            # 2.2. Извлекаем данные из open_grid
            cur.execute("""
                    SELECT first_order_in_grid, symbol, open_grid_data
                    FROM open_grid
                    WHERE first_order_in_grid = ?
                """, (first_order_in_grid,))
            result = cur.fetchone()

            if result:
                # 2.3. Вставляем данные в close_grid
                cur.execute("""
                        INSERT INTO closed_grid (first_order_in_grid, symbol, open_grid_data)
                        VALUES (?, ?, ?)
                    """, result)

                # 2.4. Удаляем данные из open_grid
                cur.execute("""
                        DELETE FROM open_grid
                        WHERE first_order_in_grid = ?
                    """, (first_order_in_grid,))

                # Фиксируем транзакцию
                cur.execute("COMMIT")
                # print(f"Транзакция для {first_order_in_grid} успешно выполнена.")
            else:
                print(f"Запись {first_order_in_grid} не найдена в open_grid.")
                cur.execute("ROLLBACK")  # откатываем транзакцию если записи нет в open_grid

    except Exception as e:
        print(f"Ошибка при выполнении транзакции: {e}")
        try:
            cur.execute("ROLLBACK")  # откатываем транзакцию при любой ошибке
            print("Транзакция отменена.")
        except:
            pass
def transfer_grid_from_closed_to_completed(first_order_in_grid):
    try:
        with sq.connect("crypto_bull.db") as con:
            cur = con.cursor()

            # Начинаем транзакцию
            cur.execute("BEGIN TRANSACTION")

            # 2.2. Извлекаем данные из open_grid
            cur.execute("""
                SELECT first_order_in_grid, symbol, open_grid_data
                FROM closed_grid
                WHERE first_order_in_grid = ?
            """, (first_order_in_grid,))
            result = cur.fetchone()

            if result:
                # 2.3. Вставляем данные в completed_grid
                cur.execute("""
                    INSERT INTO completed_grid (first_order_in_grid, symbol, open_grid_data)
                    VALUES (?, ?, ?)
                """, result)

                # 2.4. Удаляем данные из closed_grid
                cur.execute("""
                    DELETE FROM closed_grid
                    WHERE first_order_in_grid = ?
                """, (first_order_in_grid,))

                # Фиксируем транзакцию
                cur.execute("COMMIT")
                # print(f"Транзакция для {first_order_in_grid} успешно выполнена.")
            else:
                print(f"Запись {first_order_in_grid} не найдена в open_grid.")
                cur.execute("ROLLBACK") # откатываем транзакцию если записи нет в open_grid

    except Exception as e:
        print(f"Ошибка при выполнении транзакции: {e}")
        try:
            cur.execute("ROLLBACK") # откатываем транзакцию при любой ошибке
            print("Транзакция отменена.")
        except:
            pass
#функция для импорта json файлов сеток из папок
def import_orders_data_from_folders_to_base():
    # перенесем текущие сетки
    PATH = 'orders_data'
    first_order_in_grid = ""
    if os.path.exists(PATH):
        for file in os.listdir(PATH):
            # print(file)
            if "txt" not in file:
                continue
            file_path = f"{PATH}/{file}"
            with open(f"{file_path}", encoding='utf-8-sig') as json_file:
                orders_data = json.load(json_file)
            for i in orders_data["orders_data"]:  # i - это сетка ордеров, вохможно их будет несколько, возможно одна
                for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                    first_order_in_grid = key
            symbol = orders_data["orders_data"][0][key][0]["open"]["symbol"]
            # print(first_order_in_grid,symbol)
        # запишем данные текущей сетки в базу
        if first_order_in_grid != "":
            add_new_grid_to_base(first_order_in_grid,symbol,orders_data)


    # перенесем closed_grid
    PATH = 'closed_grid'
    if os.path.exists(PATH):
        for file in os.listdir(PATH):
            # print(file)
            if "txt" not in file:
                continue
            file_path = f"{PATH}/{file}"
            with open(f"{file_path}", encoding='utf-8-sig') as json_file:
                orders_data = json.load(json_file)
            for i in orders_data["orders_data"]:  # i - это сетка ордеров, вохможно их будет несколько, возможно одна
                for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                    first_order_in_grid = key
            symbol = orders_data["orders_data"][0][key][0]["open"]["symbol"]
            # print(first_order_in_grid,symbol)
            # запишем данные закрытой сетки в базу
            with sq.connect("crypto_bull.db") as con:
                # запись данных о новой сетке
                orders_data_json = json.dumps(orders_data) # Преобразуем словарь в строку JSON
                cur = con.cursor()
                try:
                    cur.execute("""
                            INSERT INTO closed_grid (first_order_in_grid, symbol, open_grid_data)
                            SELECT ?, ?, ?
                            WHERE NOT EXISTS (
                                SELECT 1
                                FROM closed_grid
                                WHERE first_order_in_grid = ?
                            )
                        """, (first_order_in_grid, symbol, orders_data_json,
                              first_order_in_grid))  # first_order_in_grid добавлен еще раз для WHERE NOT EXISTS
                    con.commit()
                    # print("Запись добавлена (если не существовала).")
                except sq.IntegrityError:  # Обработка ошибок, если столбец first_order_in_grid является UNIQUE
                    print("Ошибка: Запись с таким first_order_in_grid уже существует (UNIQUE constraint violation).")
                except Exception as e:
                    print(f"Произошла ошибка: {e}")
                con.commit()  # сохраним изменения

    # перенесем completed_grid
    PATH = 'closed_grid/completed_grid'
    if os.path.exists(PATH):
        for file in os.listdir(PATH):
            #print(file)
            if "txt" not in file:
                continue
            file_path = f"{PATH}/{file}"
            with open(f"{file_path}", encoding='utf-8-sig') as json_file:
                orders_data = json.load(json_file)
            for i in orders_data["orders_data"]:  # i - это сетка ордеров, вохможно их будет несколько, возможно одна
                for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                    first_order_in_grid = key
            symbol = orders_data["orders_data"][0][key][0]["open"]["symbol"]
            #print(first_order_in_grid,symbol)
            # запишем данные закрытой сетки в базу
            with sq.connect("crypto_bull.db") as con:
                # запись данных о новой сетке
                orders_data_json = json.dumps(orders_data) # Преобразуем словарь в строку JSON
                cur = con.cursor()
                try:
                    cur.execute("""
                            INSERT INTO completed_grid (first_order_in_grid, symbol, open_grid_data)
                            SELECT ?, ?, ?
                            WHERE NOT EXISTS (
                                SELECT 1
                                FROM completed_grid
                                WHERE first_order_in_grid = ?
                            )
                        """, (first_order_in_grid, symbol, orders_data_json,
                              first_order_in_grid))  # first_order_in_grid добавлен еще раз для WHERE NOT EXISTS
                    con.commit()
                    #print("Запись добавлена (если не существовала).")
                except sq.IntegrityError:  # Обработка ошибок, если столбец first_order_in_grid является UNIQUE
                    print("Ошибка: Запись с таким first_order_in_grid уже существует (UNIQUE constraint violation).")
                except Exception as e:
                    print(f"Произошла ошибка: {e}")
                con.commit()  # сохраним изменения
    print(f"Импорт базы данных зевершён")
    print("Можно удалить папки 'orders_data' и 'closed_grid' из корневой папки ESM_Crypto_Bull.")

# Функция проверяет, существует ли в таблице open_grid поле с заданным значением symbol.
# если result = 0, то сетки с заданным тикетом нет в таблице open_grid, если 1, то есть
def check_if_open_grid_exist(symbol):
    try:
        with sq.connect("crypto_bull.db") as con:
            cur = con.cursor()
            cur.execute("SELECT EXISTS(SELECT 1 FROM open_grid WHERE symbol = ?)", (symbol,))
            # Получаем результат запроса
            result = cur.fetchone()[0] # если result = 0, то сетки с заданным тикетом нет в таблице open_grid, если 1, то есть
            if result == 1:
                # Получим данные найденного поля (файл сетки)
                cur.execute("SELECT open_grid_data FROM open_grid WHERE symbol = ?", (symbol,))
                data = cur.fetchone()[0]
                #print(data)
            else:
                data = ""

            return result,data
    except sq.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
    finally:
        cur.close()

# Функция проверяет, существует ли в таблице open_grid поле с заданным значением symbol.
# если result = 0, то сетки с заданным тикетом нет в таблице open_grid, если 1, то есть
def check_if_closed_grid_exist(symbol):
    try:
        with sq.connect("crypto_bull.db") as con:
            cur = con.cursor()
            cur.execute("SELECT EXISTS(SELECT 1 FROM closed_grid WHERE symbol = ?)", (symbol,))
            # Получаем результат запроса
            result = cur.fetchone()[0] # если result = 0, то сетки с заданным тикетом нет в таблице open_grid, если 1, то есть
            if result == 1:
                # Получим данные найденного поля (файл сетки)
                cur.execute("SELECT open_grid_data FROM open_grid WHERE symbol = ?", (symbol,))
                data = cur.fetchone()[0]
                #print(data)
            else:
                data = ""

            return result,data
    except sq.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
    finally:
        cur.close()
##################################################
# РАБОТА С БАЗОЙ ДАННЫХ. КОНЕЦ
##################################################

# Ордер по рынку
def market_order_bybit(session,category,symbol,side,qty): #qty это quote монета, Наример "ETHUSDT" qty=10, значит покупаем эфир по рынку на 10 баксов.
    order = session.place_order(
        category=category,
        symbol=symbol,
        side=side,
        orderType="Market",
        qty=qty)
    return order

# Лимитный ордер
def limit_order_bybit(session,category,symbol,side,qty,price,timeInForce): #qty это монета, Наример "ETHUSDT" qty=0.1 price =2000, значит выставляем лимитный ордер на закупку 0,1 эфира по курсу 2000usdt
    order = session.place_order(
        category=category,
        symbol=symbol,
        side=side,
        orderType="Limit",
        qty=qty,
        price=price,
        timeInForce=timeInForce)
    return order


# информация по открытым/закрытым ордерам. В апи Get Open & Closed Orders
# orderId -
def get_open_orders(session):
    open_orders = session.get_open_orders(
        category="spot",
        symbol=None, # получить ордера только по конкретному тикету. None - по всем
        openOnly=0, # если 0, то показывает только открытые ордера, если 1, то все?
        orderFilter=None, # можно фильтровать на открытые, ордера с условаиями итд
        limit=100, # сколько ордеров выдавать
        orderId=None # получить инфу только про конкретный ордер. None - по всем
    )
    return open_orders

# Функция для получения стакана на BYBIT
#"b" - продаём, "a" - покупаем
# стакан должен выглядеть так: ASKS - цена покупки от самой изкой до самой высокой, BIDS - цена продажи от самой высокой до самой низкой
# def def_order_book_bybit(ticket):
#     # ByBit Получение списка ордеров на заданную пару, "b" - продаём, "a" - покупаем
#     currency_pair = ticket
#     orderbook_bybit = session.get_orderbook(
#         category="spot",
#         symbol=currency_pair,
#         limit=100, timeout=2).get('result')  # limit - глубина на которую заглядываем в стакан
#     order_id_bybit = ticket
#     order_asks_bybit = orderbook_bybit["a"]
#     order_bids_bybit = orderbook_bybit["b"]
#     return order_asks_bybit,order_bids_bybit


#
# def user_settings_interface(working_ticket_list,max_order_qty):
#     user_settinfs_done = 0
#     user_max_order_qty = max_order_qty
#     while user_settinfs_done != 1:
#         user_settings = {}
#         user_settings["symbol_list"] = []
#         print("!!! Для вставки ключей апи, скопируйте их с помощью команды CTRL+C,\nзатем целкните правой кнопкой мыши по шапке терминала, \nвыберите Edit -> Paste и нажмите Enter")
#         print("#" * 40)
#         user_api_key = input(f"Введите api key для Вашего субаккаунта на Bybit и нажмите Enter:")
#         user_api_secret = input(f"Введите api secret для Вашего субаккаунта на Bybit и нажмите Enter:")
#         print("#" * 40)
#         # user_settings["user_uid"] = uid
#         user_settings["user_api_key"] = user_api_key
#         user_settings["user_api_secret"] = user_api_secret
#         print("Укажите Ваш ID из личного кабинета ESM для получения уведомлений \nв телеграмм бота EMS Monitor")
#         print("Также в телеграмме зайдите в бота ESM_Monitoring_bot и нажмите старт \nили отправьте любой символ, если не делали этого ранее.")
#         print("Если Вы не хотите получать уведомления в телеграмм бота, \nвведите 0 и нажмите Enter")
#         while True:
#             print("#" * 40)
#             user_input = input(f"Введите значение:")
#             try:
#                 check = int(user_input)
#                 break
#             except Exception as e:
#                 print('Неверное значение, ID должен быть в виде целого числа')
#         user_settings["user_chat_id"] = user_input.strip()
#         print("#" * 40)
#         print("Выберите торговую пару из доступных:")
#         index = 0
#         #TODO пока убираем свою пару
#         #print(f"Введите {str(index)} и нажмите Enter для работы со своей парой")
#         available_ticket_dict = {}
#         for i in working_ticket_list:
#             index +=1
#             print(f"Введите {str(index)} и нажмите Enter для работы с {i}")
#             available_ticket_dict[str(index)] = i
#         #user_input_symbol_choose = input(f"Введите значение:")
#         while True:
#             print("#" * 40)
#             user_input_symbol_choose = input(f"Введите значение:")
#             try:
#                 check = int(user_input_symbol_choose)
#                 break
#             except Exception as e:
#                 print('Неверное значение, введите целое число')
#         if user_input_symbol_choose == "0":
#             print("Введите название пары с которой Вы хотите работать:")
#             print("#" * 40)
#             user_ticket = input(f"Введите значение:")
#             user_ticket = user_ticket.upper()
#         else:
#             user_ticket = available_ticket_dict[user_input_symbol_choose]
#         print("#" * 40)
#         print(f"Работаем с {user_ticket}")
#         # определим минимальный размер ордера и рекомендованный депозит
#         # получим данные по тикету
#         session = HTTP(
#             api_key=user_api_key,
#             api_secret=user_api_secret)
#         instruments_info = session.get_instruments_info(
#             category="spot",
#             symbol=user_ticket)
#         #print(instruments_info)
#         baseIncrement = instruments_info['result']['list'][0]['lotSizeFilter']['basePrecision']  # мин прирощение в монетах
#         priceIncrement = instruments_info['result']['list'][0]['lotSizeFilter']['quotePrecision']  # мин прирощение в баксах
#         minOrderQty = instruments_info['result']['list'][0]['lotSizeFilter']['minOrderQty']  # минимальный ордер в монетах
#         minOrderAmt = instruments_info['result']['list'][0]['lotSizeFilter']['minOrderAmt']  # минимальный ордер в баксах
#         tickSize = instruments_info['result']['list'][0]['priceFilter']['tickSize']  # минимальный ордер в баксах
#         #print(f"{baseIncrement=}\n{priceIncrement=}\n{minOrderQty=}\n{minOrderAmt=}\n{tickSize=}")
#         print("#" * 40)
#         print(f"Минимальный ордер для данной торговой пары составляет: {float(minOrderAmt)*2} USDT")
#         print(f"Выберите минимальный ордер для {user_ticket}")
#         #user_input = input(f"Введите значение:")
#         while True:
#             print("#" * 40)
#             user_input = input(f"Введите значение:")
#
#             try:
#                 user_input = float(user_input)
#                 while user_input < float(minOrderAmt) * 2:
#                     print(f"ОШИБКА! Минимальный ордер не может быть меньше {float(minOrderAmt) * 2}")
#                     user_input = input(f"Введите значение:")
#                 break
#             except Exception as e:
#                 print('Неверное значение, введите число.')
#         user_minOrderAmt = float(user_input)
#         max_order_amount = 3*user_minOrderAmt
#         if user_input_symbol_choose == "0":
#             print(f"Выберите максимальный ордер для {user_ticket}")
#             #user_input = input(f"Введите значение:")
#             while True:
#                 print("#" * 40)
#                 user_input = input(f"Введите значение:")
#                 try:
#                     user_input = float(user_input)
#                     break
#                 except Exception as e:
#                     print('Неверное значение, введите число.')
#             max_order_amount = float(user_input)
#
#             print(f"Выберите максимальное количество открытых ордеров для {user_ticket} (рекомендуется от 5 до 15)")
#             #user_input = input(f"Введите значение:")
#             while True:
#                 print("#" * 40)
#                 user_input = input(f"Введите значение:")
#                 try:
#                     check = int(user_input)
#                     break
#                 except Exception as e:
#                     print('Неверное значение, введите целое число')
#             user_max_order_qty = int(user_input)
#
#         # расчитаем рекомендованный депозит для такого мин ордера и количества ордеров в сетке
#         recomended_balance = user_minOrderAmt
#         #print(recomended_balance)
#         multiplikator = 1.1363
#         for i in range(1,user_max_order_qty):
#             new_order_amount = user_minOrderAmt*multiplikator**i
#             if new_order_amount > max_order_amount:
#                 new_order_amount = max_order_amount
#             recomended_balance += new_order_amount
#             #print(new_order_amount)
#         recomended_balance = math.ceil(recomended_balance/float(user_minOrderAmt))*float(user_minOrderAmt) + user_minOrderAmt
#         print("#" * 40)
#         print(f"Рекомендованный баланс: {recomended_balance} USDT")
#
#
#
#         #TODO формируем словарь с настройками, если пара пользовательская, то он выбирает мин ордер, макс ордрер, макс колчество открытых ордеров по данной торговой паре,
#         # если пара предустановленная, то выбирает только минимальный ордер
#         if user_input_symbol_choose == "0":
#             user_settings["symbol_list"].append({user_ticket: {"user_minOrderAmt":user_minOrderAmt,"user_maxOrderAmt":max_order_amount,"user_max_order_qty":user_max_order_qty}, "recomended_balance":recomended_balance})
#         else:
#             user_settings["symbol_list"].append({user_ticket:{"user_minOrderAmt":user_minOrderAmt, "recomended_balance":recomended_balance}})
#
#         #print(f"{user_settings=}")
#
#         print("#"*30)
#         total_user_settings = "Ваши настройки:\n"
#         total_user_settings += f"Api Key: {user_settings['user_api_key']}\nApi Secret: {user_settings['user_api_key']}\nID из личного кабинета ESM: {user_settings['user_chat_id']}\n"
#         for i in user_settings["symbol_list"]:
#             for key in i:
#                 total_user_settings += f"\n**************************\n"
#                 total_user_settings += f"{key}\n"
#                 for key_1 in i[key]:
#                     if key_1 == "user_minOrderAmt":
#                         total_user_settings += f"Минимальный размер ордера: {i[key][key_1]} USDT\n"
#                     if key_1 == "user_maxOrderAmt":
#                         total_user_settings += f"Максимальный размер ордера: {i[key][key_1]} USDT\n"
#                     if key_1 == "user_max_order_qty":
#                         total_user_settings += f"Максимальное количество открытых ордеров по данной паре: {i[key][key_1]}\n"
#                     if key_1 == "recomended_balance":
#                         total_user_settings += f"Рекомендованный баланс: {i[key][key_1]} USDT"
#
#
#         print(total_user_settings)
#         print("#"*30)
#         print("Сохранить настройки? 1-да, 2-ввести заново")
#         print("#" * 40)
#         user_input = input(f"Введите значение:")
#         if user_input == "1":
#             file_path = "user_settings.txt"
#             print("Сохраняем файл с пользовательскими настройками")
#             with open(file_path, 'w', encoding='utf-8-sig') as outfile:
#                 json.dump(user_settings, outfile, ensure_ascii=False, indent=4)
#             user_settinfs_done = 1
#         else:
#             print("Вводим настройки заново.")
#     return user_settings


##################################
# СТРАТЕГИЯ ESM_CRYPTO_BULL
##################################

# TODO тест на максимальное количество запросов стакана
# def def_order_book_bybit_endless(ticket):
#     while 1==1:
#         currency_pair = ticket
#         orderbook_bybit = session.get_orderbook(
#             category="spot",
#             symbol=currency_pair,
#             limit=100, timeout=2).get('result')  # limit - глубина на которую заглядываем в стакан
#         print(f"стакан взят {ticket}")
#
# ticket = "BTCUSDT"
# background_process1 = Thread(target=def_order_book_bybit_endless, args=(ticket,))
# background_process1.start()
# ticket = "SOLUSDT"
# background_process2 = Thread(target=def_order_book_bybit_endless, args=(ticket,))
# background_process2.start()
# ticket = "XRPUSDT"
# background_process3 = Thread(target=def_order_book_bybit_endless, args=(ticket,))
# background_process3.start()



##################################
# исходные данные
##################################
# sushka_mode = False
# grid_step = 0.5 # Шаг сетки - процент на который должна упасть цена для запуска входа в новый ордер
# grid_multiplikator = 1.2 # мультапликатор сетки
# trall_tp = 0.1 # Тралл TP 1% ТРАЛЛ ВХОДА. Это процент на которую должна поднятся цена после достижения уровня grid_step, для выставления лимитного ордера на вход в первый ордер сетки
#
# min_order_amount = 5.5 # начальный ордер 10 баксов
# max_order_amount = 3*min_order_amount
# take_profit = 0.7 # тейк профит 1%
# max_take_profit = 5 # максимальный тейк профит, если достигаем этого уровня, то закрываем сделку
# sl_take_ptofit = 0.1 # если потеряем sl_take_ptofit тейкпрофита, то выходим
# take_profit = take_profit+sl_take_ptofit
# multiplikator = 1.2
#
# max_order_qty = 10
#
# min_working_time_of_grid = 86400 # время после которого мы готовы закрывать сетку по условию прибыль =2х от убытков
# sleep_time = 300
# time_to_update_order_status = 3 # обновляем статус ордеров через каждые time_to_update_order_status секунд



# СТАНДАРТ
# sushka_mode = False
# grid_step = 0.5 # Шаг сетки - процент на который должна упасть цена для запуска входа в новый ордер
# grid_multiplikator = 1.2 # мультапликатор сетки
# trall_tp = 0.1 # Тралл TP 1% ТРАЛЛ ВХОДА. Это процент на которую должна поднятся цена после достижения уровня grid_step, для выставления лимитного ордера на вход в первый ордер сетки
#
# min_order_amount = 5.5 # начальный ордер 10 баксов
# max_order_amount = 3*min_order_amount
# take_profit = 0.7 # тейк профит 1%
# max_take_profit = 5 # максимальный тейк профит, если достигаем этого уровня, то закрываем сделку
# sl_take_ptofit = 0.1 # если потеряем sl_take_ptofit тейкпрофита, то выходим
# take_profit = take_profit+sl_take_ptofit
# multiplikator = 1.2
#
# max_order_qty = 9
#
# min_working_time_of_grid = 86400 # время после которого мы готовы закрывать сетку по условию прибыль =2х от убытков
# sleep_time = 300
# time_to_update_order_status = 3 # обновляем статус ордеров через каждые time_to_update_order_status секунд








def security_check_and_console_interface():
    ###################################
    # КОНСОЛЬНЫЙ ИНТЕРФЕЙС. НАЧАЛО
    ###################################
    sushka_mode = False
    is_change_user_setting_available = 1  # флаг можно ли менять настройки пользователю или нет. 1 - можно, 0 - нет
    exp_flag = 0  # флаг для проверки подписки, для работы режима сушки

    # max_order_qty = 10
    print("#" * 40)
    print("ESM_crypto_bull_V1.0.2.1")
    print("#" * 40)



    # прочитаем пользовательские настройки из базы
    user_add_settings_flag = 0
    while user_add_settings_flag != 1 and stop_event.is_set() != True:
        with sq.connect("crypto_bull.db") as con:
            try:
                cur = con.cursor()
                # проверим если ли запись в бд
                cur.execute("""
                                SELECT user_api_key, user_api_secret, user_chat_id,user_symbol_list, sushka_mode_list
                                FROM actually_user_settings
                            """)
                result = cur.fetchone()
                print(result)
                if result == None:  # значит поля с настройками еще нет, запишем новые настройки
                    print("Ожидаем ввода настроек пользователем.")
                    time.sleep(5)
                else:  # значит поле уже есть, прочитаем данные
                    print("Пользователь ввел данные")
                    print("Запускаем работу алгоритма.")
                    print(result)
                    user_add_settings_flag = 1

            except Exception as e:
                print(f"Ошибка при чтении данных: {e}")

    ###################################
    # КОНСОЛЬНЫЙ ИНТЕРФЕЙС. КОНЕЦ
    ###################################

    ###################################
    #ПРОВЕРКА БЕЗОПАСНОСТИ СИСТЕМЫ. НАЧАЛО
    ###################################
    security_check_flag = 0 # флаг проверки безопасности
    exp_check_flag = 0 # флаг для проверки выхода срока подписки или тестового периода

    #TODO прочитаем настройки пользователя, прочитаем ключи и исходные данные

    user_api_key= result[0]
    user_api_secret= result[1]
    user_chat_id= result[2]
    #chat_ids = (user_chat_id,'1575144075')
    chat_ids = (user_chat_id,) #куда отправлять сообщения
    user_symbol_list = result[3]
    sushka_mode_list = result[4]
    #
    # #TODO если тикетов будет несколько, то исправить код ниже
    # for i in user_settings["symbol_list"]:
    #     for key in i:
    #         ticket = key
    #     print(f"Работаем с {ticket}")
    # min_order_amount = float(user_settings["symbol_list"][0][ticket]["user_minOrderAmt"])
    # #TODO прописать возможность изменения минимального ордера, если есть открытая сетка


    # сделаем запрос от субаккаунта пользователя, для проверки uid основного аккаунта
    session = HTTP(
            api_key=user_api_key,
            api_secret=user_api_secret)
    parentUid = session.get_api_key_information()['result']['parentUid']
    print(f"{parentUid=}")



    ###################################
    #ФЛАГИ
    ###################################
    admin_module = False
    if parentUid == "130602840" or parentUid == "41085914":
    #if parentUid == "41085914":
        admin_module = True

    if parentUid == "130602840":
        demo_flag = 1
    else:
        demo_flag = 0


    if uid == parentUid:
        print("Проверка безопасности успешно пройдена.")
        security_check_flag = 1
    else:
        print("Проверка безопасности не пройдена!")

    # сделаем запрос времени на сервере байбит
    if security_check_flag == 1:
        bybit_server_time = int(session.get_server_time()['result']["timeSecond"])
        #print(bybit_server_time)
        if bybit_server_time < exp_time:
            exp_check_flag = 1
            print("Подписка активна.")
        else:
            print("Подписка не активна.")
            # если файл сетки уже создан, то разрешаем работу до окончания режима сушки
            # PATH = 'orders_data'
            # if not os.path.exists(PATH):
            #     os.makedirs(PATH)
            # file_path = 'orders_data/orders_data.txt'
            # if os.path.exists(file_path):  # если файл с сетками ордеров уже создан, прочитаем его
            #     print("Есть открытые ордера, работаем до выполнения всех ордеров.")
            #     sushka_mode = True
            #     exp_check_flag = 1
            # Базы данных БД, проверка если файл текущей сетки существует
            #TODO доработать нужно пройти по всем тикетам из настроек и запустить сушку для тух у которых есть активные сетки и после этого заблокировать работу программы по подписке

            # result = check_if_open_grid_exist(symbol=ticket)
            # if result[0] == 1:  # значит файл сетки существует
            #     # orders_data = json.loads(result[1])  # прочитаем файл сетки
            #     print("Есть открытые ордера, работаем до выполнения всех ордеров.")
            #     sushka_mode = True
            #     exp_check_flag = 1
    #
    #
    # if demo_flag ==1:
    #     grid_step = 0.3  # Шаг сетки - процент на который должна упасть цена для запуска входа в новый ордер
    #     grid_multiplikator = 1.2  # мультапликатор сетки
    #     trall_tp = 0.05  # Тралл TP 1% ТРАЛЛ ВХОДА. Это процент на которую должна поднятся цена после достижения уровня grid_step, для выставления лимитного ордера на вход в первый ордер сетки
    #
    #     min_order_amount = 10  # начальный ордер 10 баксов
    #     max_order_amount = 3 * min_order_amount
    #     take_profit = 0.3  # тейк профит 1%
    #     max_take_profit = 5  # максимальный тейк профит, если достигаем этого уровня, то закрываем сделку
    #     sl_take_ptofit = 0.1  # если потеряем sl_take_ptofit тейкпрофита, то выходим
    #     take_profit = take_profit + sl_take_ptofit
    #     multiplikator = 1.2
    #
    #     max_order_qty = 10
    #
    #     min_working_time_of_grid = 300  # время после которого мы готовы закрывать сетку по условию прибыль =2х от убытков
    #     sleep_time = 1
    #     time_to_update_order_status = 5  # обновляем статус ордеров через каждые time_to_update_order_status секунд


    #
    # if security_check_flag == 1 and exp_check_flag ==1:
    #     print(f"Выберите ticket:\nВведите 1 и нажмите Enter для работы с ETHUSDT\nВведите 2 и нажмите Enter для работы с XRPUSDT")
    #     user_ticket = input(f"Введите значение:")
    #     if user_ticket == "1":
    #         ticket = "ETHUSDT"
    #     if user_ticket == "2":
    #         ticket = "XRPUSDT"
    #     print(f"Работаем с {ticket}")
    #
    #
    #
    #
    # if demo_flag == 1:
    #     chat_ids = ('1575144075',)
    #     # ByBit
    #     session = HTTP(
    #         api_key=test_net_api_key_bybit,
    #         api_secret=test_net_trade_api_secret_key_bybit,
    #         demo=True) #работаем в тестовом режиме, заменить на False для боевого режима)
    # elif demo_flag ==0 and ticket == "ETHUSDT":
    #     session = HTTP(
    #         api_key=kolegov_sub_eth_key,
    #         api_secret=kolegov_sub_eth_secret)  # работаем в тестовом режиме, заменить на False для боевого режима)
    # elif demo_flag == 0 and ticket == "XRPUSDT":
    #     session = HTTP(
    #         api_key=kolegov_sub_xrp_key,
    #         api_secret=kolegov_sub_xrp_secret)  # работаем в тестовом режиме, заменить на False для боевого режима)

    return (demo_flag,security_check_flag,exp_check_flag,admin_module,chat_ids,session)

    ###################################
    #ПРОВЕРКА БЕЗОПАСНОСТИ СИСТЕМЫ. КОНЕЦ
    ###################################



# TODO ДИНАМИЧЕСЧКИЙ РАСЧЕТ МУЛЬТИПЛИКАТОРА. Сетку расчитываем на падение от текущей цены до 2х летнего минимума
def dynamic_multyplikator(symbol,grid_step,max_order_qty):

    # TODO ДИНАМИЧЕСЧКИЙ РАСЧЕТ МУЛЬТИПЛИКАТОРА. Сетку расчитываем на падение от текущей цены до 2х летнего минимума
    # print(f"парсим монету {symbol} {index_coin} из {len(symbol_list_on_bybit_from_top_cryptorank)}")
    kline_qty = 1  # сколько тысяч минутных свечей собираем 43 - это месяц

    time_list = []
    end = int(datetime.datetime.now().timestamp())
    time_list.append(end)
    index = 1

    # вариант за 2 года

    # for i in range(0, kline_qty):
    #     start = int(end - 60 * 1440 * 999 * index)  # это 1000 дневных свечей
    #     # start = int(end-60*9*index) # это 10 минутных свечей
    #     time_list.append(start)
    #     index += 1
    #
    # time_list = list(reversed(time_list))
    # # print(time_list)
    # # print(len(time_list))
    #
    # total_kline_list = []
    # for i in range(0, len(time_list) - 1):
    #     # print(time_list[i])
    #     kline = session.get_kline(
    #         category="spot",
    #         symbol=symbol,
    #         interval="D",
    #         start=int(str(time_list[i]) + "000"),
    #         end=int(str(time_list[i + 1]) + "000"),
    #         limit=1000
    #     )['result']['list']
    #     for i in kline:
    #         total_kline_list.append(i)
    #
    # # print(len(total_kline_list))
    # # print(total_kline_list)
    # total_kline_list = sorted(total_kline_list)  # выстраиваем все свечи в порядке возрастания по времени
    # total_kline_list = total_kline_list[-630:]  # возьмем свечи за 2 года

    # вариант за 5 лет
    for i in range(0, kline_qty):
        start = int(end - 60 * 1440 * 999 * 7 * index)  # это 1000 недельных свечей
        # start = int(end-60*9*index) # это 10 минутных свечей
        time_list.append(start)
        index += 1

    time_list = list(reversed(time_list))
    # print(time_list)
    # print(len(time_list))

    total_kline_list = []
    for i in range(0, len(time_list) - 1):
        # print(time_list[i])
        kline = session.get_kline(
            category="spot",
            symbol=symbol,
            interval="W",
            start=int(str(time_list[i]) + "000"),
            end=int(str(time_list[i + 1]) + "000"),
            limit=1000
        )['result']['list']
        for i in kline:
            total_kline_list.append(i)
    # print(f"{symbol=} история за {len(total_kline_list)/52}лет")
    # print(len(total_kline_list))
    # print(total_kline_list)
    total_kline_list = sorted(total_kline_list)  # выстраиваем все свечи в порядке возрастания по времени
    total_kline_list = total_kline_list[1:]
    total_kline_list = total_kline_list[-208:]  # возьмем свечи за 5 лет
    len_total_kline_list = len(total_kline_list)
    # print(f"{len_total_kline_list=}")


    # для дальнейшего анализа преобразуем свечи в словрь
    k_line_dict = {}
    kline_list = total_kline_list
    for k in kline_list:
        # print(f"{k=}") # Можно раскомментировать, если нужно видеть данные
        if not "open" in k_line_dict:
            k_line_dict["open"] = [float(k[1])]
        else:
            k_line_dict["open"].append(float(k[1]))
        if not 'close' in k_line_dict:
            k_line_dict['close'] = [float(k[4])]
        else:
            k_line_dict["close"].append(float(k[4]))
        if not 'high' in k_line_dict:
            k_line_dict['high'] = [float(k[2])]
        else:
            k_line_dict["high"].append(float(k[2]))
        if not 'low' in k_line_dict:
            k_line_dict['low'] = [float(k[3])]
        else:
            k_line_dict["low"].append(float(k[3]))
        if not 'volume_usdt' in k_line_dict:
            k_line_dict['volume_usdt'] = [float(k[5])]
        else:
            k_line_dict['volume_usdt'].append(float(k[5]))

    max_price = max(k_line_dict["high"])
    min_price = min(k_line_dict['low'])
    current_price = float(session.get_tickers(category="spot", symbol=symbol, )['result']['list'][0]['lastPrice'])
    # print(f"{current_price=}")
    # print(f"{min_price=}")
    # print(f"{max_price=}")
    # для работы на 5 годах умножим минимум на два
    min_price = 2*min_price
    # print(f"2х {min_price=}")

    price_reduce_from_ATH_to_ATL = (
                                               max_price - min_price) / max_price * 100  # падение монеты от макс до минимума за время выборки в процентах
    price_reduce_from_CURRENT_to_ATL = (
                                                   current_price - min_price) / current_price * 100  # падение монеты от текущей цены до минимума за время выборки в процентах
    # print(f"{price_reduce_from_ATH_to_ATL=}")
    # print(f"{price_reduce_from_CURRENT_to_ATL=}")
    # TODO расчитаем динамический мультипликатор сетки

    target_total_price_reduce = price_reduce_from_CURRENT_to_ATL

    # 2 года
    # if len(total_kline_list) < 600:
    #     target_total_price_reduce = 90
    #     print("нет истории за 2 года, расчитываем на 90% падение")

    # 5 лет
    updated_target_total_price_reduce = target_total_price_reduce
    if len_total_kline_list < 104:
        # print(len_total_kline_list)
        updated_target_total_price_reduce = 70
        # print(f"{symbol= } нет истории за 2 года, расчитываем на 70% падение")
    if target_total_price_reduce<40:
        # print(f"{symbol= } глубина ниже 40, расчитываем минимум на 40% падение")
        updated_target_total_price_reduce = 40
    # if target_total_price_reduce < 0:
    #     print(f"{symbol= } глубина ниже 0, расчитываем минимум на 70% падение")
    #     updated_target_total_price_reduce = 70
    if target_total_price_reduce > 70:
        # print(f"{symbol= } глубина больше 70, расчитываем минимум на 80% падение")
        updated_target_total_price_reduce = 70
    if current_price == min_price:
        # print(f"{symbol= } монета сейчас на историч минимуме, расчитываем сетку на 70% падение")
        updated_target_total_price_reduce = 70


    target_total_price_reduce = updated_target_total_price_reduce
    # print(f"{target_total_price_reduce=}")


    def calculate_total_price_reduce(grid_step, max_order_qty, grid_multiplikator):
        """
        Рассчитывает total_price_reduce для заданных параметров сетки.
        """
        total_price_reduce = grid_step
        for i in range(1, max_order_qty):
            new_grid_step = grid_step * grid_multiplikator ** i
            total_price_reduce += new_grid_step
        return total_price_reduce

    def find_grid_multiplikator(grid_step, max_order_qty, target_total_price_reduce, tolerance=0.1):
        """
        Находит grid_multiplikator, который дает заданный total_price_reduce, используя метод бисекции.
        Args:
            grid_step: Шаг сетки.
            max_order_qty: Максимальное количество ордеров.
            target_total_price_reduce: Желаемое значение total_price_reduce.
            tolerance: Допустимая погрешность в процентах.
        Returns:
            Приближенное значение grid_multiplikator, или None, если решение не найдено.
        """

        # Определяем границы поиска. grid_multiplikator всегда > 1 (иначе просадка не увеличивается).
        low = 1.0000001  # Нельзя использовать 1, иначе будет деление на 0 при проверке
        high = 2  # верхняя граница мультика для расчетов.

        while low <= high:
            mid = (low + high) / 2  # Находим середину текущего интервала
            current_total_price_reduce = calculate_total_price_reduce(grid_step, max_order_qty,
                                                                      mid)  # расчитываем просадку для данного мультика

            # Сравниваем текущий total_price_reduce с целевым
            if abs(
                    current_total_price_reduce - target_total_price_reduce) < tolerance:  # Если погрешность в пределах tolerance
                return mid  # Нашли grid_multiplikator

            # Корректируем границы поиска
            if current_total_price_reduce < target_total_price_reduce:
                low = mid  # Целевое значение больше, сдвигаем нижнюю границу
            else:
                high = mid  # Целевое значение меньше, сдвигаем верхнюю границу

        return None  # Решение не найдено в заданном диапазоне

    grid_multiplikator = find_grid_multiplikator(grid_step, max_order_qty, target_total_price_reduce)

    if grid_multiplikator:
        print(f"Приближенное значение grid_multiplikator: {grid_multiplikator}")
        # Проверяем результат:
        calculated_total = calculate_total_price_reduce(grid_step, max_order_qty, grid_multiplikator)
        print(f"Проверка: total_price_reduce при найденном grid_multiplikator: {calculated_total}")
    else:
        print("Не удалось найти grid_multiplikator в заданном диапазоне.")
    return grid_multiplikator

    # TODO построим свечные графики
    # make_klines_volume_plot(kline_list=total_kline_list)




#def esm_crypto_bul(demo_flag,security_check_flag,exp_check_flag,ticket,admin_module,chat_ids,preset_dict):
def esm_crypto_bul(start_data,thread_started_dict,stop_event,user_coin_names, user_bot_name, used_dinamic_take_profit,admin_module,uid,used_enter_in_grid_just_after_grid_closed):

    global is_new_message_to_tg_was_sent

    demo_flag = start_data[0]
    security_check_flag = start_data[1]
    exp_check_flag = start_data[2]
    ticket = start_data[3]
    admin_module = start_data[4]
    chat_ids = start_data[5]
    preset_dict = start_data[6]
    session = start_data[7]
    min_order_amount = start_data[8]
    persent_mode = start_data[9]

    grid_step = preset_dict[ticket]["grid_step"]
    grid_multiplikator = preset_dict[ticket]["grid_multiplikator"]
    trall_tp = preset_dict[ticket]["trall_tp"]
    # min_order_amount = preset_dict[ticket]["min_order_amount"]
    max_order_amount = preset_dict[ticket]["max_order_amount"]
    take_profit = preset_dict[ticket]["take_profit"]
    max_take_profit = preset_dict[ticket]["max_take_profit"]
    sl_take_ptofit = preset_dict[ticket]["sl_take_ptofit"]
    multiplikator = preset_dict[ticket]["multiplikator"]
    max_order_qty = preset_dict[ticket]["max_order_qty"]
    min_working_time_of_grid = preset_dict[ticket]["min_working_time_of_grid"]
    sleep_time = preset_dict[ticket]["sleep_time"]
    time_to_update_order_status = preset_dict[ticket]["time_to_update_order_status"]
    # time_to_update_order_status = preset_dict[ticket]["time_to_update_order_status"]
    sushka_mode = preset_dict[ticket]["sushka_mode"]
    min_pure_profit = preset_dict[ticket]["min_pure_profit"]

    profit_loss_ratio_to_close_grig = 3 # отношение профита к потерям в сетке
    additional_grid_fall_percent = 60 # новое для сеток длины 2х. Процент на который будет продлена сетка от значения покупки ордера под номрером max_order_qty
    max_attempt = 10  # максимальное количество попыток запросов к апи



    #TODO динамический мультипликатор
    # print(f"стандартный мультик {grid_multiplikator=}")
    dynamic_grid_multyplikator = dynamic_multyplikator(symbol=ticket, grid_step=grid_step, max_order_qty=max_order_qty)
    grid_multiplikator = dynamic_grid_multyplikator

    # если есть файл сетки, то загрузим мультик из нее
    # Базы данных БД, проверка если файл текущей сетки существует
    result = check_if_open_grid_exist(symbol=ticket)
    if result[0] == 1:  # значит файл сетки существует
        orders_data = json.loads(result[1])  # прочитаем файл сетки
        if "grid_multiplikator" in orders_data:
            grid_multiplikator = orders_data["grid_multiplikator"]
            if admin_module == True:
                print(f"динамический мультипликатор загружен из БД {grid_multiplikator=}")
    else:
        if admin_module == True:
            print(f"динамический мультипликатор {grid_multiplikator=}")

    if demo_flag == 1:
        min_working_time_of_grid = 1
        grid_step = 0.1
        grid_multiplikator = 1
        trall_tp = 0.05
        take_profit = 5
        sl_take_ptofit = 0.05
        profit_loss_ratio_to_close_grig = 0.1
        additional_grid_fall_percent = 2
        max_order_qty = 5
    # grid_step = 0.5
    # grid_multiplikator = 1.15
    # trall_tp = 0.1
    # take_profit = 0.6
    # sl_take_ptofit = 0.4
    # multiplikator = 1.1363
    # max_order_qty = 20
    # max_order_amount = min_order_amount


    if admin_module == True:
        print(f"{start_data=}")
        print(f"{grid_step=},{trall_tp=},{take_profit=},{sl_take_ptofit=}")

    ###################################
    #ЗАПУСК РАБОТЫ АЛГОРИТМА
    ###################################
    if demo_flag == 1:
        session = HTTP(
                api_key="JStaeQUBqcqGmeDo1v",
                api_secret="q0m5uEMonyMScH3AOhu0OBXgbMnWrSPQSfLv",
                demo=True) #работаем в тестовом режиме, заменить на False для боевого режима)
    # запускаем бесконечный цикл, если сетка еще не открыта, открываем и ждем пока она завершится, после этого открывается новая сетка
    # if security_check_flag == 1 and exp_check_flag ==1: # если прошли проверку безопасности - запускаем алгоритм
    if security_check_flag == 1:  # если прошли проверку безопасности - запускаем алгоритм
        sushka_completed_stop_thread = 0 # флаг, который останавливает поток, после того как сушка завершена
        # ГЛАВНЫЙ ЦИКЛ СЕТОК
        grid_counter = -1 # счектчик количества сеток в потоке
        while sushka_completed_stop_thread != 1 and stop_event.is_set() != True: # если этот флаг будет равен 1, то поток полностью завершится и закроется методом join
            if used_enter_in_grid_just_after_grid_closed == True:
                grid_counter +=1
            # print(f"стоп ивент из потока {stop_event.is_set()}")
            # перепроверим exp flag
            bybit_server_time = int(session.get_server_time()['result']["timeSecond"])
            exp_flag = 0
            if bybit_server_time > exp_time:
                exp_flag = 1 # подписка не активна
                # Базы данных БД, проверка если файл текущей сетки существует
                result = check_if_open_grid_exist(symbol=ticket)
                if result[0] == 0:  # значит файл сетки не существует
                    print(f"ПОДПИСКА НЕ АКТИВИРОВАНА, ОБРАТИТЕСЬ К АДМИНИСТРАТОРУ! {ticket}")
                    sushka_completed_stop_thread = 1
                    ts = time.time()
                    console_message = f"ПОДПИСКА НЕ АКТИВИРОВАНА, ОБРАТИТЕСЬ К АДМИНИСТРАТОРУ! {ticket}"
                    svodkda_massage = f"{ticket} ПОДПИСКА НЕ АКТИВИРОВАНА"
                    console_message_dict = {"message": console_message, "ts": ts, "svodkda_massage":svodkda_massage}
                    with lock:
                        if ticket not in total_console_message_dict:
                            total_console_message_dict[ticket] = {}
                    with lock:
                        total_console_message_dict[ticket] = console_message_dict
                    break
                else:
                    print("ПОДПИСКА НЕ АКТИВИРОВАНА, но есть открытая сетка, включаем режим сушки для этой сетки")
                    sushka_mode = True # принудительно включаем режим сушки


            previous_socket_price = 0
            try:

                # если сетка уже существует, то возьмем мин ордер из первого ордера сетки
                result = check_if_open_grid_exist(symbol=ticket)
                if result[0] == 1:  # значит файл сетки существует
                    orders_data = json.loads(result[1])  # прочитаем файл сетки
                    # if admin_module == True:
                    #     print("БД файл сетки существует. откроем файл")
                    # print(orders_data)
                    for i in orders_data["orders_data"]:
                        for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                            first_order_in_grid = key
                            first_grid_order_amount = round(float(i[key][0]["open"]['cumExecValue']), 0)
                            # print(first_grid_order_amount)
                            min_order_amount = first_grid_order_amount

                else:   # если сетки нет, то обновимся с настроек
                    #TODO обновим мин ордер из пользовательских настроек во время начала новой сетки
                    with sq.connect("crypto_bull.db") as con:
                        try:
                            cur = con.cursor()
                            # проверим если ли запись в бд
                            cur.execute("""SELECT user_symbol_list FROM actually_user_settings""")
                            result = cur.fetchone()
                        except Exception as e:
                            print(f"Ошибка при чтении данных: {e}")
                    user_coin_settings_dict = json.loads(result[0])
                    min_order_amount = float(user_coin_settings_dict[ticket.lower()]["amount"]) # прочитаем мин ордер из настроек пользователя
                    persent_mode = user_coin_settings_dict[ticket.lower()]["percent_mode"] # прочитаем persent_mode из настроек пользователя

                    #TODO пересчитаем мин ордер, если persent_mode = true
                    if persent_mode == True:
                        max_order_qty = max_order_qty
                        percent_from_dep_to_coint = min_order_amount # процент который указал пользователь
                        totalEquity_enought_to_work_with_coin = False
                        while totalEquity_enought_to_work_with_coin != True and stop_event.is_set() != True:
                            try:
                                # определим эквити субаккаунта
                                totalEquity = float(session.get_wallet_balance(accountType="UNIFIED", )['result']['list'][0]['totalEquity'])
                                # print(totalEquity)
                                # определим минимальный возможный ордер по монете
                                instruments_info = session.get_instruments_info(category="spot", symbol=ticket)
                                minOrderAmt = float(instruments_info['result']['list'][0]['lotSizeFilter']['minOrderAmt'])  # минимальный ордер в баксах
                                minOrderAmt = math.ceil(minOrderAmt * 1.15)  # добавим 15% и округлим в большую сторону, чтобы не получить ордер на продажу с недостаточным количеством монет
                                # print(f"{minOrderAmt=}")
                                # расчитаем сумму которую пользователь выделил на монету и расчетный мин ордер
                                deposite_to_coin = totalEquity * percent_from_dep_to_coint / 100
                                deposite_to_coin = 200
                                counted_min_order_amount = deposite_to_coin / max_order_qty / 2
                                # print(f"{deposite_to_coin=}")
                                # print(f"{counted_min_order_amount=}")

                                if counted_min_order_amount < minOrderAmt:
                                    print(f"Недостаточно средств для работы с {ticket}")
                                    console_message = f"Недостаточно средств для работы с {ticket}"
                                    svodkda_massage = f"{ticket} Недостаточно средств"
                                    ts = time.time()
                                    console_message_dict = {"message": console_message, "ts": ts, "svodkda_massage":svodkda_massage}
                                    # print(console_message_dict)
                                    with lock:
                                        if ticket not in total_console_message_dict:
                                            total_console_message_dict[ticket] = {}
                                    with lock:
                                        total_console_message_dict[ticket] = console_message_dict
                                    # print(total_console_message_dict)
                                    time.sleep(20)  # ждем пока увеличится эквити
                                else:
                                    min_order_amount = round(counted_min_order_amount,2)  # начинаем работу с монетой
                                    totalEquity_enought_to_work_with_coin = True
                            except Exception as ex:
                                print(ex)

                        # print("начинаем работу с монетой")
                        print(f"Авторазгон {ticket}, эквити {totalEquity}usdt, процент от депозита {percent_from_dep_to_coint}. Расчитанный мин ордер {min_order_amount}")
                        # print(total_console_message_dict)




                profit_messege_send_list = [] # сюда складываем айди ордеров по которым отправили сообщения
                #############################################
                # TODO визуализация работы алгоритма
                #############################################
                plot_make_flag = 1  # флаг будем стоить графики сеток или нет
                #############################################

                is_new_coin_price_to_open_new_order_added = 0
                console_message_timer = 0
                # словарь сетки для постоения графика, значениями будут картежи (время взятия стакана, цена)
                if plot_make_flag == 1:
                    plot_orders_data = {}
                    if "ask_price" not in plot_orders_data:  # все аски на каждом шаге взятия стаканов
                        plot_orders_data["ask_price"] = []

                    if "stat_price" not in plot_orders_data:  # начальная цена перед входом в первую связку сетки + значения цены, если будем её переставлять выше
                        plot_orders_data["stat_price"] = []

                    if "grid_step_triger" not in plot_orders_data:  # все достижения шага цены для каждого нового ордера сетки
                        plot_orders_data["grid_step_triger"] = []
                    if "grid_step_tral" not in plot_orders_data:  # тянем вход в ордер (все значения для каждого ордера сетки)
                        plot_orders_data["grid_step_tral"] = []
                    if "open_order_price" not in plot_orders_data:  # цена входа в новый ордер сетки
                        plot_orders_data["open_order_price"] = []

                    if "tp_close_triger" not in plot_orders_data:  # все достижения тригера тейкпрофита для каждого нового ордера сетки
                        plot_orders_data["tp_close_triger"] = []
                    if "tp_close_tral" not in plot_orders_data:  # тянем выход из ордера (все значения для каждого ордера сетки)
                        plot_orders_data["tp_close_tral"] = []
                    if "close_order_price" not in plot_orders_data:  # цена выхода из ордера сетки
                        plot_orders_data["close_order_price"] = []


                #############################################
                #############################################
                # ШАГ 1 - входим в сетку
                #############################################
                #############################################
                # получим данные по тикету
                instruments_info = session.get_instruments_info(
                    category="spot",
                    symbol=ticket)
                baseIncrement = instruments_info['result']['list'][0]['lotSizeFilter']['basePrecision']  # мин прирощение в монетах
                priceIncrement = instruments_info['result']['list'][0]['lotSizeFilter']['quotePrecision']  # мин прирощение в баксах
                minOrderQty = instruments_info['result']['list'][0]['lotSizeFilter']['minOrderQty']  # минимальный ордер в монетах
                minOrderAmt = instruments_info['result']['list'][0]['lotSizeFilter']['minOrderAmt']  # минимальный ордер в баксах
                tickSize = instruments_info['result']['list'][0]['priceFilter']['tickSize']  # минимальный ордер в баксах
                #print(f"{baseIncrement=}\n{priceIncrement=}\n{minOrderQty=}\n{minOrderAmt=}\n{tickSize=}")

                timer_1 = datetime.datetime.now().timestamp()
                # если файла с сеткой еще нет, выполним вход в первый ордер сетки
                # PATH = 'orders_data'
                # if not os.path.exists(PATH):
                #     os.makedirs(PATH)
                # file_path = 'orders_data/orders_data.txt'
                # if not os.path.exists(file_path):  # если файл с сетками ордеров уже создан, прочитаем его
                #     print(f"{sushka_mode=}")
                #     print("Открываем первый ордер")
                # Базы данных БД, проверка если файл текущей сетки существует
                result = check_if_open_grid_exist(symbol=ticket)
                if result[0] == 0:  # значит файл сетки не существует

                    print("Открываем первый ордер")
                    # print(f"{sushka_mode=}")
                    # if exp_flag == 1:
                    #     sushka_mode = True
                    # if sushka_mode == True:
                    #     print("Включен режим сушки, открытие новых ордеров запрещено,\nпоменяйте режим сушки в интерфейсе на вкладке СУШКА!")
                    #     sushka_completed_stop_thread = 1
                    #     break
                        # print("Если Вы хотете изменить пользовательские настройки - закройте файл алгоритма и откройте его заново.")
                        # sushka_user_input = input("Выключить режим сушки и возобновить работу алгоритма?\nДля выключения режима сушки введите любой символ:")
                        # if sushka_user_input and exp_flag == 0:
                        #     sushka_mode = False
                        # else:
                        #     while 1==1:
                        #         print("ПОДПИСКА НЕ АКТИВИРОВАНА, ОБРАТИТЕСЬ К АДМИНИСТРАТОРУ!")
                        #         time.sleep(5)
                    # ШАГ 1 - выставляем лимитный ордер на закупку ниже текущей цены на Тралл TP, если цена растет, то тянем цену закупки за собой

                    # получим стакан
                    # orderbook = def_order_book_bybit(ticket=ticket)
                    # start_price_ask_1 = float(orderbook[0][0][0])
                    # start_price_bid_1 = float(orderbook[1][0][0])
                    last_price = session.get_tickers(category="spot", symbol=ticket, )['result']['list'][0]['lastPrice']
                    start_price_ask_1 = float(last_price)
                    start_price_bid_1 = float(last_price)
                    if admin_module == True:
                        print(f"{start_price_ask_1=},{start_price_bid_1=}")
                    if plot_make_flag == 1:
                        plot_timer = datetime.datetime.now().timestamp()
                        plot_orders_data["ask_price"].append((plot_timer, start_price_ask_1))
                        plot_orders_data["stat_price"].append((plot_timer, start_price_ask_1))


                    # определим цену после падения на шаг сетки
                    grid_step_price = start_price_ask_1 * (1 - grid_step / 100)
                    # будем следить за ценой, пока она не упадет на шаг сетки
                    # file_path = 'orders_data/orders_data.txt'
                    # if not os.path.exists(file_path):  # если файл с сетками ордеров еще не создан, то откроем стартовый ордер первой сетки
                    #     is_price_low_on_grid_step = 0
                    result = check_if_open_grid_exist(symbol=ticket)
                    if result[0] == 0:  # значит файл сетки не существует # если файл с сетками ордеров еще не создан, то откроем стартовый ордер первой сетки
                        is_price_low_on_grid_step = 0
                        first_step_timer = 0
                        while sushka_completed_stop_thread != 1 and stop_event.is_set() != True:

                            # print(f"стоп ивент из потока {stop_event.is_set()}")
                            if time.time() - first_step_timer > 10:
                                console_message = f"########################################\n{ticket} поиск точки входа\n########################################\n"
                                svodkda_massage = f"{ticket} поиск точки входа"
                                ts = time.time()
                                console_message_dict = {"message": console_message, "ts": ts, "svodkda_massage":svodkda_massage}
                                with lock:
                                    if ticket not in total_console_message_dict:
                                        total_console_message_dict[ticket] = {}
                                with lock:
                                    total_console_message_dict[ticket] = console_message_dict
                                first_step_timer = time.time()

                                # #TODO сетки еще нет, а шушка включена - закрываем поток
                                # каждые 10 секунд считываем из базы состояние режима сушки
                                with sq.connect("crypto_bull.db") as con:
                                    try:
                                        cur = con.cursor()
                                        # проверим если ли запись в бд
                                        cur.execute("SELECT sushka_mode_list FROM actually_user_settings")
                                        result = json.loads(cur.fetchone()[0])
                                        # print(result)
                                        sushka_mode = result[ticket.lower()]
                                        # print(f"{sushka_mode=}")
                                    except Exception as e:
                                        print(f"Ошибка при чтении данных: {e}")
                                if sushka_mode == True:
                                    sushka_completed_stop_thread = 1
                                    endless_cicle_stop = 1
                                    print(f"СУШКА завершена, закрываем алгоритм для {ticket}")
                                    try:
                                        # message = f"profit={round(profit, 3)}"
                                        for chatid in chat_ids:
                                            if user_bot_name == "":
                                                user_bot_name = "CRYPTO BULL"
                                            message = f"СУШКА ЗАВЕРШЕНА! {ticket} {user_bot_name}"
                                            if demo_flag == 1:
                                                message += "DEMO!!!"
                                            bot.send_message(chatid, message)
                                            with lock:
                                                is_new_message_to_tg_was_sent = True
                                    except Exception as ex:
                                        print(ex)
                                    # завершаем поток
                                    with lock:
                                        thread_started_dict[ticket] = False  # отмечаем в словаре. что потока с этой монетой нет
                                    # нужно удалить записи из БД в столбцах настроек монеты и настроек сушки
                                    with sq.connect("crypto_bull.db") as con:
                                        try:
                                            cur = con.cursor()
                                            # проверим если ли запись в бд
                                            cur.execute("""
                                                                                                SELECT user_api_key, user_api_secret, user_chat_id,user_symbol_list, sushka_mode_list
                                                                                                FROM actually_user_settings
                                                                                            """)
                                            result = cur.fetchone()
                                            user_symbol_list = json.loads(result[3])
                                            sushka_mode_list = json.loads(result[4])
                                            print(user_symbol_list, sushka_mode_list)
                                            update_user_symbol_list = {}
                                            update_sushka_mode_list = {}
                                            for key in user_symbol_list:
                                                if key != ticket.lower():
                                                    update_user_symbol_list[key] = user_symbol_list[key]
                                            for key in sushka_mode_list:
                                                if key != ticket.lower():
                                                    update_sushka_mode_list[key] = sushka_mode_list[key]
                                            print(update_user_symbol_list)
                                            print(update_sushka_mode_list)

                                            # обновим данные в БД
                                            update_user_symbol_list = json.dumps(
                                                update_user_symbol_list)  # Преобразуем словарь в строку JSON
                                            update_sushka_mode_list = json.dumps(update_sushka_mode_list)
                                            # изменяем данные в столбце
                                            try:
                                                cur = con.cursor()
                                                cur.execute("""
                                                                                                        UPDATE actually_user_settings 
                                                                                                        SET user_symbol_list = ?, sushka_mode_list = ?
                                                                                                        WHERE user_api_key = ?
                                                                                                    """,
                                                            (update_user_symbol_list, update_sushka_mode_list,
                                                             result[0]))  # Параметризованный запрос
                                                con.commit()  # сохраним изменения
                                            except Exception as e:
                                                print(f"Ошибка при обновлении данных: {e}")


                                        except Exception as e:
                                            print(f"Ошибка при чтении данных: {e}")
                                    break

                                # print(f"{total_console_message_dict=}")
                            # orderbook = def_order_book_bybit(ticket=ticket)
                            # price_ask_1 = float(orderbook[0][0][0])
                            # price_bid_1 = float(orderbook[1][0][0])
                            last_price = session.get_tickers(category="spot", symbol=ticket, )['result']['list'][0][
                                'lastPrice']
                            price_ask_1 = float(last_price)
                            price_bid_1 = float(last_price)
                            if plot_make_flag == 1:
                                plot_timer = datetime.datetime.now().timestamp()
                                plot_orders_data["ask_price"].append((plot_timer, price_ask_1))
                                if len(plot_orders_data["stat_price"]) == 0:
                                    plot_orders_data["stat_price"].append((plot_timer, price_ask_1))
                            # TODO если цена пошла вверх переставляем grid_step_price, уточнить нужно ли это делать и уточнить насчет триггера за несколько тиков до входа
                            if price_ask_1 > start_price_ask_1:
                                grid_step_price = price_ask_1 * (1 - grid_step / 100)  # изменим grid_step_price на новый
                                start_price_ask_1 = price_ask_1  # изменим start_price_ask_1 на новый
                                if admin_module == True:
                                    print("Цена выросла - переставим grid_step_price")
                                if plot_make_flag == 1:
                                    plot_orders_data["stat_price"].append((plot_timer, price_ask_1))
                            if price_ask_1 <= grid_step_price:
                                if admin_module == True:
                                    print("Цена монеты упала на щаг сетки или ниже, выставляем ордер на вход выше, начинаем тянуть сделку и готовиться к входу")
                                if plot_make_flag == 1:
                                    plot_orders_data["grid_step_triger"].append((plot_timer, price_ask_1))
                                is_price_low_on_grid_step = 1
                                grid_step_price = price_ask_1  # перезапишем grid_step_price

                                start_order_price = price_ask_1 * (1 + trall_tp / 100)  # определим цену по которой будем входить и приведем ее в кратный вид

                            if used_enter_in_grid_just_after_grid_closed == True and grid_counter > 0: # входим сразу если это не первая сетка
                                print("сетка не первая входим сразу")
                                is_price_low_on_grid_step = 1

                            # TODO входить нам нужно только если цена пойдет вверх и заденет триггер на вход, триггер на вход поставим на пару тиков ниже чем start_order_price
                            # если цена пойдет вниз, то будем редактировать триггерный ордер
                            # альтернативный вариант - следить за ценой и выставить просто лимитный ордер когда цена заденет триггер

                            if is_price_low_on_grid_step == 1:
                                # проверяем цену, если цена выростет до trall_tp, выставляем лимитку на вход в первый ордер сетки

                                if price_ask_1 >= start_order_price - 3 * float(tickSize) or used_enter_in_grid_just_after_grid_closed == True and grid_counter > 0:  # триггером на выставление лимитной заявки считаем момент когда цена не дошла 3 тика до start_order_price
                                    if admin_module == True:
                                        if used_enter_in_grid_just_after_grid_closed == True:
                                            print("сетка не первая входим сразу")
                                        print(f"цена выросла на чем трал ТП от grid_step, входим в сделку. Цена сейчас {price_bid_1}, начальная цена шага сетки {grid_step_price}")
                                    if plot_make_flag == 1:
                                        plot_orders_data["open_order_price"].append((plot_timer, price_ask_1))
                                    # выставляем лимитный ордер на покупку
                                    # расчитаем цену и объем для входа
                                    start_order_price = price_ask_1 + price_ask_1 * 2 * sl_take_ptofit / 100  # определим цену по которой будем входить и приведем ее в кратный вид
                                    # increment_start_order_price = round(start_order_price / float(priceIncrement)) * float(priceIncrement)
                                    increment_start_order_price = start_order_price
                                    increment_start_order_price = round(increment_start_order_price, len(str(tickSize).split(".")[1]))  # округлим цену закупки до tickSize


                                    # start_order_price = price_ask_1  # определим цену по которой будем входить и приведем ее в кратный вид
                                    # # increment_start_order_price = round(start_order_price / float(priceIncrement)) * float(priceIncrement)
                                    # # increment_start_order_price = round(increment_start_order_price, len(
                                    # #     str(tickSize).split(".")[1]))  # округлим цену закупки до tickSize
                                    # increment_start_order_price = start_order_price
                                    #print(f"{start_order_price=},{increment_start_order_price=}")

                                    # определим объем ордера в монетах и приведем его в кратный вид
                                    start_order_size = min_order_amount / start_order_price
                                    increment_start_order_size = round(start_order_size / float(baseIncrement)) * float(
                                        baseIncrement)
                                    increment_start_order_size = round(increment_start_order_size, len(
                                        str(baseIncrement).split(".")[
                                            1]))  # еще раз округлим, чтобы убрать 000000000001, округляем на количество знаков после запятой у baseIncrement
                                    #print(len(str(baseIncrement).split(".")[1]))
                                    #print(f"{start_order_size=},{increment_start_order_size=}")
                                    # выставляем лимитный ордер на покупку и закрываем цикл поиска точки входа в первый ордер сетки и выставления ордера на вход
                                    # выставляем лимитный ордер на покупку и закрываем цикл поиска точки входа в первый ордер сетки и выставления ордера на вход
                                    try:
                                        limit_order = limit_order_bybit(session=session, category="spot", symbol=ticket,
                                                                        side="Buy",
                                                                        qty=str(increment_start_order_size),
                                                                        price=str(increment_start_order_price), timeInForce="GTC")
                                    except Exception as ex:
                                        tb_str = traceback.format_exc()
                                        time_error = datetime.datetime.now()
                                        log_file = 'Error_logger.txt'
                                        limit_order = ex
                                        try:
                                            if admin_module:
                                                tb_str = traceback.format_exc()
                                                log_text = f"ОШИБКА В limit_order {time_error}\n{ex}\n{tb_str}\n"
                                                print(
                                                    f"ОШИБКА В limit_order {time_error}\n{ex}\n{tb_str}\n")
                                            else:
                                                log_text = f"ОШИБКА В limit_order {time_error}\n{ex}\n"
                                                print(ex)
                                            with open(log_file, 'a+', encoding='utf-8-sig') as file:
                                                file.write(log_text)
                                        except Exception as e:
                                            print(f"Не удалось записать в лог-файл: {e}")
                                    orderId = limit_order['result']['orderId']
                                    if admin_module == True:
                                        print(f"{limit_order=}\n{orderId=}")
                                    break

                # Проверяем состояние первого ордера и ждем пока он будет заполнен
                timer_2 = datetime.datetime.now().timestamp()
                # file_path = 'orders_data/orders_data.txt'
                # if not os.path.exists(
                #         file_path):  # если файл с сетками ордеров еще не создан, то откроем стартовый ордер первой сетки
                # # Базы данных БД, проверка если файл текущей сетки существует
                result = check_if_open_grid_exist(symbol=ticket)
                if result[0] == 0:  # значит файл сетки не существует
                    print("Открываем первый ордер")
                    first_step_timer = 0
                    while sushka_completed_stop_thread != 1 and stop_event.is_set() != True:
                        # print(f"стоп ивент из потока {stop_event.is_set()}")
                        if time.time() - first_step_timer > 10:
                            console_message = f"########################################\n{ticket} поиск точки входа\n########################################\n"
                            svodkda_massage = f"{ticket} поиск точки входа"
                            ts = time.time()
                            console_message_dict = {"message": console_message, "ts": ts, "svodkda_massage":svodkda_massage}
                            with lock:
                                if ticket not in total_console_message_dict:
                                    total_console_message_dict[ticket] = {}
                            with lock:
                                total_console_message_dict[ticket] = console_message_dict
                            first_step_timer = time.time()
                            # print(f"{total_console_message_dict=}")
                        # TODO тут наверное тоже нужно брать стаканы и проверять если цена упала, то редактировать лимитный ордер
                        # orderbook = def_order_book_bybit(ticket=ticket)
                        # price_ask_1 = float(orderbook[0][0][0])
                        last_price = session.get_tickers(category="spot", symbol=ticket, )['result']['list'][0][
                            'lastPrice']
                        price_ask_1 = float(last_price)
                        price_bid_1 = float(last_price)
                        if price_ask_1 <= grid_step_price:
                            if admin_module == True:
                                print("Цена монеты упала еще ниже, отредактируем лимитный ордер")
                            # расчитаем новую цену и объем для входа
                            start_order_price = price_ask_1 * (1 + trall_tp / 100)  # определим цену по которой будем входить и приведем ее в кратный вид
                            amend_increment_start_order_price = round(start_order_price / float(priceIncrement)) * float(priceIncrement)
                            amend_increment_start_order_price = round(amend_increment_start_order_price, len(str(tickSize).split(".")[1]))  # округлим цену закупки до tickSize
                            if admin_module == True:
                                print(f"{start_order_price=},{amend_increment_start_order_price=}")
                            # определим объем ордера в монетах и приведем его в кратный вид
                            start_order_size = min_order_amount / start_order_price
                            amend_increment_start_order_size = round(start_order_size / float(baseIncrement)) * float(baseIncrement)
                            amend_increment_start_order_size = round(amend_increment_start_order_size, len(str(baseIncrement).split(".")[1]))  # еще раз округлим, чтобы убрать 000000000001, округляем на количество знаков после запятой у baseIncrement
                            if admin_module == True:
                                print(f"{start_order_size=},{amend_increment_start_order_size=}")
                            # редактируем стартовый ордер
                            try:
                                if increment_start_order_price != amend_increment_start_order_price or increment_start_order_size != amend_increment_start_order_size:  # если цена или объем изменилимь от изначальных после приведения к кратному виду
                                    if admin_module == True:
                                        print("редактируем ордер!")
                                    session.amend_order(
                                        category="spot",
                                        symbol=ticket,
                                        orderId=str(orderId),
                                        qty=str(amend_increment_start_order_size),
                                        price=str(amend_increment_start_order_price)
                                    )

                                    grid_step_price = price_ask_1  # перезапишем grid_step_price
                                    increment_start_order_price = amend_increment_start_order_price  # изменим стартовую цену закупки на новую
                                    increment_start_order_size = amend_increment_start_order_size  # изменим стартовый объем закупки на новый
                            except Exception as ex:
                                if admin_module == True:
                                    print("ордер уже закрылся, редактирование невозможно")
                                print(ex)

                        # проверяем статус стартового ордера, если он заполнен, или заполнен частично, то прерываем цикл
                        # order_details = session.get_open_orders(category="spot", orderId=orderId)
                        attempt = 0
                        while attempt < max_attempt:
                            order_details = session.get_open_orders(category="spot", orderId=orderId)
                            retMsg = order_details['retMsg']
                            data_order = order_details['result']['list']
                            if retMsg == "OK" and data_order != []:
                                break
                            attempt += 1
                            order_details = "NO CORRECT DATA"
                            time.sleep(1)
                        if order_details == "NO CORRECT DATA":
                            try:
                                message = f"ОШИБКА. При выставлении ордера на открытие первого ордера сетки, апи не вернуло order_details. UID = {uid}"
                                if demo_flag == 1:
                                    message += "DEMO!!!"
                                bot.send_message(chatid="1575144075", message=message)
                            except Exception as ex:
                                print(ex)
                        order_status = order_details['result']['list'][0]["orderStatus"]
                        order_id = order_details['result']['list'][0]["orderId"]
                        order_symbol = order_details['result']['list'][0]["symbol"]
                        if admin_module == True:
                            print(f"{order_details=},{order_status=}")
                        # order_details={'retCode': 0, 'retMsg': 'OK', 'result': {'nextPageCursor': '1903028001650773248%3A1741594616072%2C1903028001650773248%3A1741594616072', 'category': 'spot', 'list': [{'symbol': 'ETHUSDT', 'orderType': 'Limit', 'orderLinkId': '1903028001650773249', 'slLimitPrice': '0', 'orderId': '1903028001650773248', 'cancelType': 'UNKNOWN', 'avgPrice': '0.00', 'stopOrderType': '', 'lastPriceOnCreated': '', 'orderStatus': 'New', 'takeProfit': '0', 'cumExecValue': '0.0000000', 'smpType': 'None', 'triggerDirection': 0, 'blockTradeId': '', 'isLeverage': '0', 'rejectReason': 'EC_NoError', 'price': '2046.58', 'orderIv': '', 'createdTime': '1741594616072', 'tpTriggerBy': '', 'positionIdx': 0, 'trailingPercentage': '0', 'timeInForce': 'GTC', 'leavesValue': '10.0077762', 'basePrice': '2067.1', 'updatedTime': '1741594616073', 'side': 'Buy', 'smpGroup': 0, 'triggerPrice': '0.00', 'tpLimitPrice': '0', 'trailingValue': '0', 'cumExecFee': '0', 'leavesQty': '0.00489', 'slTriggerBy': '', 'closeOnTrigger': False, 'placeType': '', 'cumExecQty': '0.00000', 'reduceOnly': False, 'activationPrice': '0', 'qty': '0.00489', 'stopLoss': '0', 'marketUnit': '', 'smpOrderId': '', 'triggerBy': ''}]}, 'retExtInfo': {}, 'time': 1741594616342}
                        timer_3 = datetime.datetime.now().timestamp()
                        if order_status == "Filled":
                            print("Стартовый ордер открыт")
                            print(f"Время на поиск точки входа стартового ордера {round(timer_2 - timer_1)}сек")
                            print(f"Время на заполнения стартового ордера {round(timer_3 - timer_2)}сек")
                            break


                # # открываем/создаем json файл для первого ордера в сетке
                # # создаем папку orders_data и json файл в которой будем хранить данные
                # PATH = 'orders_data'
                # if not os.path.exists(PATH):
                #     os.makedirs(PATH)
                #
                # file_path = 'orders_data/orders_data.txt'
                # if os.path.exists(file_path): # если файл с сетками ордеров уже создан, прочитаем его
                #     with open(f"{file_path}", encoding='utf-8-sig') as json_file:
                #         orders_data = json.load(json_file)


                #Базы данных БД, проверка если файл текущей сетки существует
                result = check_if_open_grid_exist(symbol=ticket)
                if result[0] == 1: # значит файл сетки существует
                    orders_data = json.loads(result[1]) # прочитаем файл сетки

                    # if admin_module == True:
                    #     print("БД файл сетки существует")
                # for i in orders_data["orders_data"]:
                #     for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                #         first_order_in_grid = key
                # else:
                elif result[0] == 0 and sushka_completed_stop_thread != 1: # создадим файл с ордерами
                    # orders_data = {}
                    # orders_data["orders_data"] = []
                    # data_dict = {}
                    # data_dict["first_grid_order"] = order_details['result']['list'][0]
                    # orders_data["orders_data"].append(data_dict)
                    orders_data = {}
                    orders_data["orders_data"] = []
                    data = order_details['result']['list'][0]
                    first_in_grid_order_id = order_details['result']['list'][0]["orderId"]
                    orders_data["orders_data"].append({first_in_grid_order_id:[{"open":data}]})
                    # динамический мультпликатор. добавим мультк сетки в файл сетки
                    orders_data["grid_multiplikator"] = grid_multiplikator


                    # # Запись JSON в файл
                    # with open(f"{file_path}", 'w', encoding='utf-8-sig') as outfile:
                    #     json.dump(orders_data, outfile)

                    #Базы данных БД. запись данных новой сетки в БД
                    first_order_in_grid = first_in_grid_order_id
                    symbol = ticket
                    orders_data = orders_data
                    add_new_grid_to_base(first_order_in_grid=first_order_in_grid, symbol=ticket, orders_data=orders_data)




                #############################################
                # ШАГ 2 - выставляем ордера на продажу, открываем новые ордера сетки
                #############################################

                # выставляем лимитный ордер на продажу
                # пройдем по orders_data и выставим ордер на продажу
                #TODO заполнять словарь triger_data_dict
                triger_data_dict = {} # сюда будем складывать новые тригеры для каждого ордера
                order_status_update_time = 0

                endless_cicle_stop = 0
                timer_endless_cicle_start = 0
                timer_endless_cicle_end = 0
                time_check_sushka_mode_list = 0
                close_order_3x_process_started = False  # флаг что начали тянуть по 3х
                while endless_cicle_stop != 1 and stop_event.is_set() != True and sushka_completed_stop_thread != 1:
                    # print(f"стоп ивент из потока {stop_event.is_set()}")
                    if used_dinamic_take_profit == True:
                        take_profit = preset_dict[ticket]["take_profit"] # каждую итерацию обновим тп до начального, это для использования динамического ТП
                    # каждые 10 секунд считываем из базы состояние режима сушки
                    if time.time() - time_check_sushka_mode_list > 10:
                        with sq.connect("crypto_bull.db") as con:
                            try:
                                cur = con.cursor()
                                # проверим если ли запись в бд
                                cur.execute("SELECT sushka_mode_list FROM actually_user_settings")
                                result = json.loads(cur.fetchone()[0])
                                #print(result)
                                time_check_sushka_mode_list = time.time()
                                sushka_mode = result[ticket.lower()]
                                #print(sushka_mode)
                            except Exception as e:
                                print(f"Ошибка при чтении данных: {e}")
                    if exp_flag == 1: #если подписка не активна - флаг сушки всегда включен!
                        sushka_mode = True

                    #print(f"{triger_data_dict=}")
                    circle_period = timer_endless_cicle_end-timer_endless_cicle_start
                    if circle_period > 0.25 and socket_flag ==1:
                        if uid == '130602840':
                            print(f"Время круга endless_cicle:{round(circle_period,4)}")
                    timer_endless_cicle_start = time.time()
                    # TODO это нужно сделать асинхронной функцией
                    ################################
                    # КОНТРОЛЬ И ОБНОВЛЕНИЕ СТАТУСОВ ОРДЕРОВ. НАЧАЛО
                    ################################
                    timer_1 = datetime.datetime.now().timestamp()
                    if timer_1 - order_status_update_time > time_to_update_order_status: # если прошло время между обновлениями статусов ордеров
                        #print("проверяем статус ордеров")
                        # проверяем состояние всех ордеров сеток
                        # получим все открытые (только статусы New или PartiallyFilled). Если ордера здесь нет, то он Filled или отменет
                        open_orders = session.get_open_orders(
                            category="spot",
                            symbol=ticket, # получить ордера только по конкретному тикету. None - по всем
                            openOnly=1,  # если 0, то показывает только открытые ордера, если 1, то все?
                            limit=500,  # сколько ордеров выдавать
                            orderId=None  # получить инфу только про конкретный ордер. None - по всем
                        )['result']['list']
                        #print(open_orders)
                        # open_orders = session.get_open_orders(category="spot", orderId="1905877902428474624")['result']['list']
                        timer_2 = datetime.datetime.now().timestamp()
                        #print(open_orders)
                        #print(f"время на получение данных по ордерам {timer_2 - timer_1}")
                        # время на получение данных по ордерам - если 500 ордеров - 0,98сек, 100 - 0,75-0,9сек , 1 ордер - 0,44сек
                        # # откроем файл orders_data
                        # file_path = 'orders_data/orders_data.txt'
                        # if os.path.exists(file_path):  # если файл с сетками ордеров уже создан, прочитаем его
                        #     with open(f"{file_path}", encoding='utf-8-sig') as json_file:
                        #         orders_data = json.load(json_file)

                        # Базы данных БД, откроем файл orders_data если файл текущей сетки уже существует
                        result = check_if_open_grid_exist(symbol=ticket)
                        if result[0] == 1: # значит файл сетки существует
                            orders_data = json.loads(result[1]) # прочитаем файл сетки
                            # if admin_module == True:
                            #     print("БД файл сетки существует. откроем файл")
                        for i in orders_data["orders_data"]:
                            for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                                first_order_in_grid = key


                        # print(f"{orders_data=}")
                        # идем по orders_data и обновляем статусы всех наших ордеров из сеток в соответствии со списком open_orders
                        for i in orders_data["orders_data"]:  # i - это сетка ордеров, вохможно их будет несколько, возможно одна
                            index = 0
                            for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                                first_grid_order_id = key
                                #print(f"{key=}")
                                orders_index = 0
                                for orders in i[key]:  # i[key] это все ордера сетки, в том числе и первый, orders - это словарь с данными {open:..., close:...}
                                    # print(orders)
                                    usdt_qty_to_buy_coin = float(orders["open"]['cumExecValue'])
                                    for orders_key in orders:
                                        order_id = orders[orders_key]["orderId"]
                                        #print(order_id)
                                        for c in open_orders:
                                            if c['orderId'] == order_id:
                                                if orders[orders_key]["orderStatus"] != "Filled":
                                                    #print("нашли соответствующий ордер, обновим данные")
                                                    orders_data["orders_data"][index][key][orders_index][orders_key] = c
                                                    if c['orderStatus'] == "Filled" and orders_key == "close": # если ордер закрылся и он был close ордером, если убрать close, то будут приходить открытия которые исполнились не мгновенно
                                                        # отпарвим пользователю сообщение о закрытом ордере
                                                        cumExecValue = float(c["cumExecValue"])
                                                        cumExecFee = float(c["cumExecFee"])
                                                        profit = cumExecValue - cumExecFee - usdt_qty_to_buy_coin
                                                        profit_percent = round(profit/usdt_qty_to_buy_coin*100,2)
                                                        #print(f"{profit=}")
                                                        try:
                                                            # message = f"profit={round(profit, 3)}"
                                                            for chatid in chat_ids:
                                                                if user_bot_name == "":
                                                                    user_bot_name = "CRYPTO BULL"
                                                                message = f"💵 {round(profit, 3)}$ | {profit_percent}% \u25B2 {ticket} {user_bot_name}"
                                                                if demo_flag == 1:
                                                                    message += "DEMO!!!"
                                                                bot.send_message(chatid, message)
                                                                with lock:
                                                                    is_new_message_to_tg_was_sent = True
                                                        except Exception as ex:
                                                            print(ex)
                                    orders_index += 1
                            index += 1
                        # print(f"{orders_data=}")
                        # # перезапишем файл
                        # with open(f"{file_path}", 'w', encoding='utf-8-sig') as outfile:
                        #     json.dump(orders_data, outfile)
                        # timer_3 = datetime.datetime.now().timestamp()


                        # Базы данных БД, перезапишем файл текущей сетки
                        first_order_in_grid = first_grid_order_id
                        orders_data = orders_data
                        update_open_grid_on_base(first_order_in_grid,orders_data)


                        #print(f"время на обновление данных по ордерам и перезапись файла {timer_3 - timer_2}")

                        # # проверим закрлись ли последние ордера из завершенных сеток
                        # directory = 'closed_grid'
                        # if not os.path.exists(directory):
                        #     os.makedirs(directory)
                        # # directory = 'orders_data_historical/plot_orders_data_historical'
                        # timer_4 = datetime.datetime.now().timestamp()
                        #
                        # for file in os.listdir(directory):
                        #     #print(file)
                        #     if "txt" not in file:
                        #         continue
                        #
                        #     file_path = f"{directory}/{file}"
                        #     with open(f"{file_path}", encoding='utf-8-sig') as json_file:
                        #         orders_data = json.load(json_file)
                        #
                        #     for i in orders_data[
                        #         "orders_data"]:  # i - это сетка ордеров, вохможно их будет несколько, возможно одна
                        #         index = 0
                        #         # close_orders_in_grid_counter = 0
                        #         for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                        #             #first_grid_order_id = key
                        #             # total_orders_in_grid = len(i[key])
                        #             # print(f"{key=}")
                        #             orders_index = 0
                        #             for orders in i[key]:  # i[key] это все ордера сетки, в том числе и первый, orders - это словарь с данными {open:..., close:...}
                        #                 usdt_qty_to_buy_coin = float(orders["open"]['cumExecValue'])
                        #                 # print(orders)
                        #                 for orders_key in orders:
                        #                     order_id = orders[orders_key]["orderId"]
                        #                     # print(order_id)
                        #                     for c in open_orders:
                        #                         if c['orderId'] == order_id:
                        #                             #print(orders[orders_key]["orderStatus"])
                        #                             if orders[orders_key]["orderStatus"] != "Filled":
                        #                                 #print("нашли соответствующий ордер, обновим данные")
                        #                                 orders_data["orders_data"][index][key][orders_index][orders_key] = c
                        #                                 if c['orderStatus'] == "Filled":
                        #                                     # отпарвим пользователю сообщение о закрытом ордере
                        #                                     cumExecValue = float(c["cumExecValue"])
                        #                                     cumExecFee = float(c["cumExecFee"])
                        #                                     profit = cumExecValue - cumExecFee - usdt_qty_to_buy_coin
                        #                                     #print(f"{profit=}")
                        #                                     try:
                        #                                         # message = f"profit={round(profit, 3)}"
                        #                                         for chatid in chat_ids:
                        #                                             message = f"💵 {round(profit, 3)}$ \u25B2 {ticket} CRYPTO BULL"
                        #                                             if demo_flag == 1:
                        #                                                 message += "DEMO!!!"
                        #                                             bot.send_message(chatid, message)
                        #                                     except Exception as ex:
                        #                                         print(ex)
                        #                 orders_index += 1
                        #         index += 1
                        #     # перезапишем файл
                        #     with open(f"{file_path}", 'w', encoding='utf-8-sig') as outfile:
                        #         json.dump(orders_data, outfile)
                        #
                        #     # проверим полностью ли закрылась сетка, если закрылась полностью, то перенесем сетку в папку completed_grid
                        #     PATH = 'closed_grid/completed_grid'
                        #     if not os.path.exists(PATH):
                        #         os.makedirs(PATH)
                        #     for i in orders_data[
                        #         "orders_data"]:  # i - это сетка ордеров, вохможно их будет несколько, возможно одна
                        #         close_orders_in_grid_counter = 0
                        #         for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                        #             #print(f"i[key]={i[key]}")
                        #             total_orders_in_closed_grid = len(i[key])
                        #             # print(f"{key=}")
                        #             orders_index = 0
                        #             for orders in i[
                        #                 key]:  # i[key] это все ордера сетки, в том числе и первый, orders - это словарь с данными {open:..., close:...}
                        #                 if "open" in orders and "close" in orders:
                        #                     if orders["open"]["orderStatus"] == "Filled" and orders["close"][
                        #                         "orderStatus"] == "Filled":
                        #                         close_orders_in_grid_counter += 1
                        #         if total_orders_in_closed_grid == close_orders_in_grid_counter:
                        #             #print("Сетка закрыта полностью")
                        #             # перенесем файл в папку с полностью закрытыми ордерами
                        #             os.replace(file_path, f"closed_grid/completed_grid/{file}")






                        # Базы данных БД, контроль closed_grid. НАЧАЛО

                        # проверим закрлись ли последние ордера из завершенных сеток
                        with sq.connect("crypto_bull.db") as con:
                            cur = con.cursor()
                            # Извлекаем данные из closed_grid
                            cur.execute("""
                                    SELECT open_grid_data
                                    FROM closed_grid
                                """)
                            result = cur.fetchall()
                            # print(f"{result=}")
                            # print(len(result))
                            for i in result: # идем по файлам сеток
                                orders_data = i[0]
                                orders_data = json.loads(orders_data)  #это файл сетки
                                # print(orders_data)
                                for i in orders_data["orders_data"]:  # i - это сетка ордеров, вохможно их будет несколько, возможно одна
                                    index = 0
                                    # close_orders_in_grid_counter = 0
                                    for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                                        first_order_in_grid = key
                                        # total_orders_in_grid = len(i[key])
                                        # print(f"{key=}")
                                        orders_index = 0
                                        for orders in i[
                                            key]:  # i[key] это все ордера сетки, в том числе и первый, orders - это словарь с данными {open:..., close:...}
                                            usdt_qty_to_buy_coin = float(orders["open"]['cumExecValue'])
                                            # print(orders)
                                            for orders_key in orders:
                                                order_id = orders[orders_key]["orderId"]
                                                # print(order_id)
                                                for c in open_orders:
                                                    if c['orderId'] == order_id:
                                                        # print(orders[orders_key]["orderStatus"])
                                                        if orders[orders_key]["orderStatus"] != "Filled":
                                                            # print("нашли соответствующий ордер, обновим данные")
                                                            orders_data["orders_data"][index][key][orders_index][
                                                                orders_key] = c
                                                            if c['orderStatus'] == "Filled":
                                                                # отпарвим пользователю сообщение о закрытом ордере
                                                                cumExecValue = float(c["cumExecValue"])
                                                                cumExecFee = float(c["cumExecFee"])
                                                                profit = cumExecValue - cumExecFee - usdt_qty_to_buy_coin
                                                                profit_percent = round(
                                                                    profit / usdt_qty_to_buy_coin * 100, 2)

                                                                # print(f"{profit=}")
                                                                try:
                                                                    # message = f"profit={round(profit, 3)}"
                                                                    for chatid in chat_ids:
                                                                        if user_bot_name == "":
                                                                            user_bot_name = "CRYPTO BULL"
                                                                        message = f"💵 {round(profit, 3)}$ | {profit_percent}% \u25B2 {ticket} {user_bot_name}"
                                                                        if demo_flag == 1:
                                                                            message += "DEMO!!!"
                                                                        bot.send_message(chatid, message)
                                                                        with lock:
                                                                            is_new_message_to_tg_was_sent = True
                                                                except Exception as ex:
                                                                    print(ex)
                                            orders_index += 1
                                    index += 1

                                # обновим данные об закрытой сетке
                                update_order_data_json = json.dumps(orders_data)  # Преобразуем словарь в строку JSON
                                try:
                                    cur = con.cursor()
                                    cur.execute("""
                                                    UPDATE closed_grid 
                                                    SET open_grid_data = ? 
                                                    WHERE first_order_in_grid = ?
                                                """, (
                                    update_order_data_json, first_order_in_grid))  # Параметризованный запрос
                                    con.commit()  # сохраним изменения
                                except Exception as e:
                                    print(f"Ошибка при обновлении данных: {e}")

                                # проверим полностью ли закрылась сетка, если закрылась полностью, то перенесем сетку в папку completed_grid
                                for i in orders_data["orders_data"]:  # i - это сетка ордеров, вохможно их будет несколько, возможно одна
                                    close_orders_in_grid_counter = 0
                                    for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                                        # print(f"i[key]={i[key]}")
                                        total_orders_in_closed_grid = len(i[key])
                                        # print(f"{key=}")
                                        orders_index = 0
                                        for orders in i[key]:  # i[key] это все ордера сетки, в том числе и первый, orders - это словарь с данными {open:..., close:...}
                                            if "open" in orders and "close" in orders:
                                                if orders["open"]["orderStatus"] == "Filled" and orders["close"]["orderStatus"] == "Filled" or orders["open"]["orderStatus"] == "PartiallyFilledCanceled" and orders["close"]["orderStatus"] == "Filled":
                                                    close_orders_in_grid_counter += 1
                                    if total_orders_in_closed_grid == close_orders_in_grid_counter:
                                        # print("Сетка закрыта полностью")
                                        # сетка полностью исполнена, переносим запись в completed_grid, а в closed_grid удаляем
                                        transfer_grid_from_closed_to_completed(first_order_in_grid)

                        # Базы данных БД, контроль closed_grid. КОНЕЦ
                        timer_5 = datetime.datetime.now().timestamp()
                        # print(f"время на обновление данных по ордерам и перезапись файла {timer_5 - timer_4}")
                        order_status_update_time = datetime.datetime.now().timestamp()

                        ################################
                        # КОНТРОЛЬ И ОБНОВЛЕНИЕ СТАТУСОВ ОРДЕРОВ. КОНЕЦ
                        ################################

                    #TODO это будет работать только если в файле orders_data может быть только одна сетка!!!! если нет, то для каждой сетки в файле нужно расчитывать total_open_orders_in_grid отдельно

                    # file_path = 'orders_data/orders_data.txt'
                    # if os.path.exists(file_path):  # если файл с сетками ордеров уже создан, прочитаем его
                    #     with open(f"{file_path}", encoding='utf-8-sig') as json_file:
                    #         orders_data = json.load(json_file)

                    # Базы данных БД, проверка если файл текущей сетки существует, откроем файл текущей сетки
                    result = check_if_open_grid_exist(symbol=ticket)
                    if result[0] == 1: # значит файл сетки существует
                        orders_data = json.loads(result[1]) # прочитаем файл сетки
                        # if admin_module == True:
                        #     print("БД файл сетки существует")
                    for i in orders_data["orders_data"]:
                        for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                            first_order_in_grid = key


                    # определим общее количество открытых ордеров сетки на данный момент, исключая ордера которые уже закрылись
                    for i in orders_data["orders_data"]:
                        total_open_orders_in_grid_counter = 0
                        for key in i.keys():
                            open_orders_list = []
                            for orders in i[key]:
                                if "open" in orders and "close" not in orders:
                                    total_open_orders_in_grid_counter += 1
                                    open_orders_list.append(orders)
                    total_open_orders_in_grid = total_open_orders_in_grid_counter
                    #last_open_order_id = open_orders_list[-1]['open']['orderId'] # это для того чтобы определять coin_price_to_open_new_order, он будет равен coin_price_to_open_new_order самого нижнего открытого ордера в сетке, так определяем каждое взятие стакана
                    #print(f"{last_open_order_id=}")

                    for i in orders_data["orders_data"]: # i - это сетка ордеров, вохможно их будет несколько, возможно одна
                        close_orders_in_grid_counter = 0
                        for key in i.keys(): # key это айди первого ордера в сетке, по сути это ключ к сетке
                            #print(f"{key=}")
                            first_order_id_in_grid = key
                            # print("sdfsdf")
                            # print(i[key][0])
                            start_time_of_grid = int(i[key][0]["open"]["createdTime"][0:-3]) # время старта сетки
                            # print(start_time_of_grid)
                            # получим стакан
                            timer_4 = datetime.datetime.now().timestamp()
                            # orderbook = def_order_book_bybit(ticket=ticket)
                            # price_ask_1 = float(orderbook[0][0][0])
                            # price_bid_1 = float(orderbook[1][0][0])
                            #TODO проверим цену из сокета, если она свежая, то исполльзуем её
                            #print("socket_price")
                            with lock:
                                if "socket_price" in locals() and ticket in price_dict:
                                    if len(price_dict[ticket])>0:
                                        socket_price = price_dict[ticket][-1]["current_price"]
                                        socket_ts = price_dict[ticket][-1]["ts"]
                                else:
                                    socket_price = 0
                                    socket_ts = 0
                            # print("previous_socket_price")
                            #print(socket_price,previous_socket_price)
                            if socket_price != 0:
                                if socket_price == previous_socket_price:
                                    if uid == "130602840":
                                        time.sleep(0.05)
                                    else:
                                        time.sleep(0.275)
                                    # if admin_module == True:
                                    #     print("цена монеты не изменилась, пропускаем")
                                    continue
                                else:
                                    if uid == "130602840":
                                        print("цена монеты изменилась, выполняем расчеты")
                                    if uid != "130602840":
                                        time.sleep(0.275)
                                time_now = datetime.datetime.now().timestamp()
                                # print(f"socket time delta {round(time_now - socket_ts,2)}")

                                # if time_now - socket_ts < 1 or socket_ts - time_now < 1:
                                if time_now - socket_ts < 1 or socket_ts - time_now < 0.01: # цена сокета не старее 1 сек
                                    socket_flag = 1
                                    # if admin_module == True:
                                    #     print("цена актуальная, работаем по сокету")
                                    price_ask_1 = price_dict[ticket][-1]["current_price"]
                                    price_bid_1 = price_ask_1
                                    previous_socket_price = price_ask_1 # обновим previous_socket_price
                                else:
                                    socket_flag = 0
                                    last_price = session.get_tickers(category="spot", symbol=ticket, )['result']['list'][0][
                                        'lastPrice']
                                    price_ask_1 = float(last_price)
                                    price_bid_1 = float(last_price)
                            else:
                                # if admin_module == True:
                                #     print("цена сокета устарела, работаем по запросу")
                                socket_flag = 0
                                last_price = session.get_tickers(category="spot", symbol=ticket, )['result']['list'][0][
                                    'lastPrice']
                                price_ask_1 = float(last_price)
                                price_bid_1 = float(last_price)
                            # print(f"{price_ask_1=} from endless cicle")
                            if plot_make_flag == 1:
                                plot_timer = datetime.datetime.now().timestamp()
                                plot_orders_data["ask_price"].append((plot_timer, price_ask_1))
                            total_orders_in_grid = len(i[key]) # общее количество открытых ордеров в сетке, включая первый
                            total_open_orders_in_grid = total_open_orders_in_grid # это общее количество открытых ордеров сетки на данный момент, исключая ордера которые уже закрылись
                            for orders in i[key]: # i[key] это все ордера сетки, в том числе и первый, orders - это словарь с данными {open:..., close:...}
                                # print(f"сетка {i[key]}")
                                is_it_first_grid_order = 0 # флаг для определения работаем с первым ордером в сетке или нет
                                is_order_status_filled = 0 # флаг завершен ли ордер на вход, если нет, то пропускаем и ждем пока он исполнится
                                # if orders["open"]["orderStatus"] == "PartiallyFilled":
                                #     message = f'{orders["open"]["orderId"]} PartiallyFilled'
                                #     print(message)
                                #     bot.send_message("1575144075", message)

                                if key==orders["open"]["orderId"]:
                                    #print("значит это первый ордер в сетке")
                                    is_it_first_grid_order = 1

                                    if orders["open"]["orderStatus"] == "Filled" or orders["open"]["orderStatus"] == "PartiallyFilled":
                                        is_order_status_filled = 1
                                        order_id = orders["open"]["orderId"]
                                        coin_qty_to_sell = float(orders["open"]['cumExecQty']) #TODO возможно нужно брать 'qty', проверить
                                        price_coin_buyed = float(orders["open"]['avgPrice'])  #TODO возможно нужно брать 'price', проверить
                                        price_coin_buyed_start_order = price_coin_buyed
                                        usdt_qty_to_buy_coin = float(orders["open"]['cumExecValue'])
                                        cumExecFee = float(orders["open"]['cumExecFee']) # комиссия в МОНЕТАХ если ордер BUY и в USDT если SELL, непонятно учтена она в 'cumExecQty' или нет, проверить. СКОРЕЕ ВСЕГО НЕ УЧТЕНА и нужно вычитать cumExecFee из cumExecQty чтобы получить реальный объем который у нас есть
                                        #расчитаем динамический тейкпрофик
                                        if used_dinamic_take_profit == True:
                                            min_order_amount_for_dinamac_tp = usdt_qty_to_buy_coin
                                            fee = 0.2
                                            dust_from_close = float(baseIncrement)
                                            start_order_price_for_dinamic_tp = price_coin_buyed
                                            # print(f"{ticket=}, мин ордер={min_order_amount_for_dinamac_tp} базовый ТП {take_profit=}")
                                            take_profit = ((min_pure_profit / 100 + 1) * min_order_amount_for_dinamac_tp / (
                                                        1 - fee / 100) / ((min_order_amount_for_dinamac_tp / start_order_price_for_dinamic_tp * (
                                                        1 - fee / 100)) - dust_from_close)
                                                               / start_order_price_for_dinamic_tp + sl_take_ptofit / 100 - 1) * 100
                                            # print(f"Динамический ТР расчет из первого ордера {take_profit=}")

                                        coin_price_to_sell = price_coin_buyed*(1+take_profit/100) # цена по которой купили + процент тэйкпрофит
                                        max_coin_price_to_sell = price_coin_buyed * (1 + max_take_profit / 100)

                                        #coin_price_to_open_new_order = price_coin_buyed*(1-prise_down_to_open_new_order/100) # цена по которой купили - процент при котором открывается новая сделка с мультипликатором
                                        # TODO новые ордера в сетке должны открываться также с мультипликатором сетки в геометрической прогрессии
                                        #coin_price_to_open_new_order = price_coin_buyed*(1-grid_step/100) # цена по которой купили - процент при котором открывается новая сделка с мультипликатором
                                        coin_price_to_open_new_order = price_coin_buyed*(1-grid_step*grid_multiplikator/100) # цена по которой купили - процент при котором открывается новая сделка с мультипликатором * мультипликатор сетки в степени равной количеству открытых ордеров
                                        #coin_price_to_open_new_order = price_coin_buyed*(1-trall_tp/100) # цена по которой купили - процент при котором открывается новая сделка с мультипликатором * мультипликатор сетки в степени равной количеству открытых ордеров
                                        #print(f"{coin_qty_to_sell=}\n{price_coin_buyed=}\n{usdt_qty_to_buy_coin=}\n{coin_price_to_sell=}\n{coin_price_to_open_new_order=}")
                                        if orders["open"]["orderId"] not in triger_data_dict:
                                            triger_data_dict[orders["open"]["orderId"]] = {}
                                        if "coin_qty_to_sell" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["coin_qty_to_sell"] = coin_qty_to_sell
                                        if "price_coin_buyed" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["price_coin_buyed"] = price_coin_buyed
                                        if "usdt_qty_to_buy_coin" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["usdt_qty_to_buy_coin"] = usdt_qty_to_buy_coin
                                        if "cumExecFee" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["cumExecFee"] = cumExecFee
                                        if "coin_price_to_sell" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["coin_price_to_sell"] = coin_price_to_sell
                                        if "max_coin_price_to_sell" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["max_coin_price_to_sell"] = max_coin_price_to_sell
                                        if "coin_price_to_open_new_order" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order"] = coin_price_to_open_new_order
                                        if "start_coin_price_to_open_new_order" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["start_coin_price_to_open_new_order"] = coin_price_to_open_new_order
                                        if "min_order_amount" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["min_order_amount"] = min_order_amount
                                        if "coin_price_to_open_new_order_list" not in triger_data_dict[orders["open"]["orderId"]]:
                                            # if admin_module == True:
                                            #     print(f"{total_orders_in_grid=}")
                                            if total_orders_in_grid > 1: # значит открылись с файла, восстановим список тригеров шага сетки
                                                # TODO после перезапуска сетки, работа продолжается с фала сетки, при этом теряетмя coin_price_to_open_new_order_list, нужно его восстановить с помощью файла сетки
                                                triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order_list"] = []
                                                copy_orders_data = orders_data["orders_data"]
                                                for b in orders_data["orders_data"]:  # i - это сетка ордеров, вохможно их будет несколько, возможно одна
                                                    index = 0
                                                    for key in b.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                                                        first_grid_order_id = key
                                                        # print(f"{key=}")
                                                        orders_index = 0
                                                        for orders_b in b[key]:  # i[key] это все ордера сетки, в том числе и первый, orders - это словарь с данными {open:..., close:...}
                                                            # TODO определим количество открытых ордеров на данном шаге итерирования по сетке
                                                            for c in copy_orders_data:
                                                                total_open_orders_in_grid_counter = 0
                                                                for key_c in c.keys():
                                                                    open_orders_list = []
                                                                    for orders_b in c[key_c][0:orders_index + 1]:
                                                                        if "open" in orders_b and "close" not in orders_b:
                                                                            total_open_orders_in_grid_counter += 1
                                                                            open_orders_list.append(orders)
                                                            # if admin_module == True:
                                                            #     print(open_orders_list)
                                                            total_open_orders_in_grid_1 = total_open_orders_in_grid_counter
                                                            #last_open_order_id = open_orders_list[-1]['open']['orderId']
                                                            # print(f"{total_open_orders_in_grid=}")
                                                            # print(f"{last_open_order_id=}")
                                                            # print(orders)
                                                            usdt_qty_to_buy_coin = float(orders["open"]['cumExecValue'])
                                                            for orders_key in orders_b:
                                                                order_id = orders_b[orders_key]["orderId"]
                                                                #print(order_id)
                                                                if orders_key == "open":
                                                                    price_coin_buyed = float(orders_b[orders_key]["avgPrice"])
                                                                    coin_price_to_open_new_order = price_coin_buyed * (
                                                                                1 - grid_step * grid_multiplikator ** total_open_orders_in_grid_1 / 100)  # цена по которой купили - процент при котором открывается новая сделка с мультипликатором * мультипликатор сетки в степени равной количеству открытых ордеров
                                                                    #print(f"{price_coin_buyed=}\n{coin_price_to_open_new_order=}\nratio: {round(price_coin_buyed / coin_price_to_open_new_order, 5)}")
                                                                    if "close" not in orders_b:
                                                                        triger_data_dict[first_grid_order_id]["coin_price_to_open_new_order_list"].append(coin_price_to_open_new_order)
                                                            orders_index += 1
                                                    index += 1
                                                triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order"] = triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order_list"][-1] #обновим цену coin_price_to_open_new_order из файла, без этого в момент запуска с файла он считает, что первый шаг сетки - это шаг сетки первого рддера
                                            else:
                                                triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order_list"] = []
                                                triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order_list"].append(coin_price_to_open_new_order)
                                        # # шаг сетки будем определять как шаг на котором был открыт последний открытый ордер сетки, это для того чтобы работать в диапазоне сразу за последний открытым ордером
                                        # print("len(list(triger_data_dict.keys()))")
                                        # print(len(list(triger_data_dict.keys())))
                                        # print(f"{triger_data_dict=}")
                                        # if len(list(triger_data_dict.keys())) > 1:
                                        #     if "coin_price_to_open_new_order" in triger_data_dict[orders["open"]["orderId"]]:
                                        #         if orders["open"]["orderId"] in triger_data_dict and last_open_order_id in triger_data_dict:
                                        #             triger_data_dict[orders["open"]["orderId"]]['coin_price_to_open_new_order'] = triger_data_dict[last_open_order_id]['coin_price_to_open_new_order']
                                        #             print(f'определили шаг сетки coin_price_to_open_new_order={triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order"]}, {last_open_order_id=}')

                                else: # не первый ордер в сетке
                                    #print("дочерний ордер в сетке")
                                    order_id = orders["open"]["orderId"]
                                    # print(f"{order_id=}")
                                    if orders["open"]["orderStatus"] == "Filled" or orders["open"]["orderStatus"] == "PartiallyFilled":
                                        is_order_status_filled = 1
                                        coin_qty_to_sell = float(orders["open"]['cumExecQty'])  # TODO возможно нужно брать 'qty', проверить
                                        price_coin_buyed = float(orders["open"]['avgPrice'])  # TODO возможно нужно брать 'price', проверить
                                        usdt_qty_to_buy_coin = float(orders["open"]['cumExecValue'])
                                        cumExecFee = float(orders["open"]['cumExecFee'])  # комиссия в монетах, непонятно учтена она в 'cumExecQty' или нет, проверить. СКОРЕЕ ВСЕГО НЕ УЧТЕНА и нужно вычитать cumExecFee из cumExecQty чтобы получить реальный объем который у нас есть
                                        # расчитаем динамический тейкпрофик
                                        if used_dinamic_take_profit == True:
                                            min_order_amount_for_dinamac_tp = usdt_qty_to_buy_coin
                                            fee = 0.2
                                            dust_from_close = float(baseIncrement)
                                            start_order_price_for_dinamic_tp = price_coin_buyed
                                            # print(f"{ticket=}, мин ордер={min_order_amount_for_dinamac_tp} базовый ТП {take_profit=}")
                                            take_profit = ((min_pure_profit / 100 + 1) * min_order_amount_for_dinamac_tp / (
                                                    1 - fee / 100) / ((min_order_amount_for_dinamac_tp / start_order_price_for_dinamic_tp * (
                                                    1 - fee / 100)) - dust_from_close)
                                                           / start_order_price_for_dinamic_tp + sl_take_ptofit / 100 - 1) * 100
                                            # print(f"Динамический ТР из других ордеров {take_profit=}")

                                        coin_price_to_sell = price_coin_buyed * (1 + take_profit / 100)  # цена по которой купили + процент тэйкпрофит
                                        max_coin_price_to_sell = price_coin_buyed * (1 + max_take_profit / 100)
                                        #TODO высчитать это от цены входа в эту сделку!!!
                                        #coin_price_to_open_new_order = price_coin_buyed*(1-grid_step*grid_multiplikator/100) # цена по которой купили - процент при котором открывается новая сделка с мультипликатором * мультипликатор сетки в степени равной количеству открытых ордеров
                                        coin_price_to_open_new_order = price_coin_buyed*(1-grid_step*grid_multiplikator**total_open_orders_in_grid/100) # цена по которой купили - процент при котором открывается новая сделка с мультипликатором * мультипликатор сетки в степени равной количеству открытых ордеров

                                        # новое для работы с сетками длины 2х
                                        if total_open_orders_in_grid > max_order_qty:
                                            # price_of_max_order_qty_order = triger_data_dict[first_order_id_in_grid]["coin_price_to_open_new_order_list"][max_order_qty] # цена по которой должен открываться последний ордер из max_order_qty сетки
                                            # coin_price_to_open_new_order = price_of_max_order_qty_order * (1 - (additional_grid_fall_percent/max_order_qty) * (total_open_orders_in_grid-max_order_qty+1) / 100)
                                            # coin_price_to_open_new_order = triger_data_dict[first_order_id_in_grid]["coin_price_to_open_new_order_list"][total_open_orders_in_grid-1] * (1 - (additional_grid_fall_percent/max_order_qty) / 100)
                                            coin_price_to_open_new_order = triger_data_dict[first_order_id_in_grid]["coin_price_to_open_new_order_list"][-1] * (1 - (additional_grid_fall_percent/max_order_qty) / 100)



                                        #coin_price_to_open_new_order = price_coin_buyed*(1-trall_tp/100) # цена по которой купили - процент при котором открывается новая сделка с мультипликатором * мультипликатор сетки в степени равной количеству открытых ордеров

                                        #print(f"{coin_qty_to_sell=}\n{price_coin_buyed=}\n{usdt_qty_to_buy_coin=}\n{coin_price_to_sell=}")
                                        if orders["open"]["orderId"] not in triger_data_dict:
                                            triger_data_dict[orders["open"]["orderId"]] = {}
                                        if "coin_qty_to_sell" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["coin_qty_to_sell"] = coin_qty_to_sell
                                        if "price_coin_buyed" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["price_coin_buyed"] = price_coin_buyed
                                        if "usdt_qty_to_buy_coin" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["usdt_qty_to_buy_coin"] = usdt_qty_to_buy_coin
                                        if "cumExecFee" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["cumExecFee"] = cumExecFee
                                        if "coin_price_to_sell" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["coin_price_to_sell"] = coin_price_to_sell
                                        if "max_coin_price_to_sell" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["max_coin_price_to_sell"] = max_coin_price_to_sell
                                        #TODO высчитать это от цены входа в эту сделку!!!

                                        if "coin_price_to_open_new_order" not in triger_data_dict[orders["open"]["orderId"]]:
                                            triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order"] = coin_price_to_open_new_order

                                # TODO начинаем следить за ценой bid в стакане, если цена превысит нашу coin_price_to_sell, то при росте цены переставляем цену на продажу выше, а при падении цены ниже на стоплосса от тейкпрофита закрываем ордер
                                trigger_take_profit_price_reached = 0 # флаг добрались ли до цены выше или равной тейкпрофиту
                                # print(f"{triger_data_dict=}")
                                if orders["open"]["orderId"] in triger_data_dict:
                                    if "trigger_take_profit_price_reached" not in triger_data_dict[orders["open"]["orderId"]]:
                                        triger_data_dict[orders["open"]["orderId"]]["trigger_take_profit_price_reached"] = trigger_take_profit_price_reached

                                #print("ШАГ 2")
                                # TODO вот тут поидее нужно каждый раз открывать json файл, пропускать закрытые ордера в сетке, отпределять сколько ордеров в сетке открыто, и проверять условия закрытия по каждому из них
                                start_take_profit_price = coin_price_to_sell

                                if is_it_first_grid_order == 1: # если это первый ордер в сетке
                                    start_coin_price_to_open_new_order = coin_price_to_open_new_order # первоначальная цена для открытия нового ордера, возможно она не нужна, а нужна coin_price_to_open_new_order, которую будем переставлять после открытия нового ордера
                                    # if "start_coin_price_to_open_new_order" not in triger_data_dict[orders["open"]["orderId"]]:
                                    #     triger_data_dict[orders["open"]["orderId"]]["start_coin_price_to_open_new_order"] = start_coin_price_to_open_new_order

                                #############################
                                # УСЛОВИЯ ДЛЯ ВЫХОДА ИЗ СДЕЛКИ
                                #############################
                                #TODO часто возникают неисполненные лимитные ордера, со статусом New, чтобы по ним корректно работать нужно постоянно проверять их состояние и менять статус на Filled после исполнения ордера
                                # либо ставить при открытии ордера условие FOK или работать по рыночным ордерам!!!

                                if is_order_status_filled == 1: # если ордер на вход исполнен, и не запущен режим выхода по 3х
                                    if "close" not in orders.keys(): # проверка если ордера на выход еще нет, а если он уже открыт - пропускаем этот шаг
                                        #print(f"{triger_data_dict=}")
                                        #if price_bid_1 >= coin_price_to_sell:
                                        if price_bid_1 >= triger_data_dict[orders["open"]["orderId"]]["coin_price_to_sell"]:
                                            if admin_module == True:
                                                print("Цена стала выше чем тейкпрофит, начинаем тянуть сделку и готовиться к выходу")
                                            if plot_make_flag == 1:
                                                plot_timer = datetime.datetime.now().timestamp()
                                                plot_orders_data["tp_close_triger"].append((plot_timer, price_ask_1))
                                            #Цена стала выше чем тейкпрофит, начинаем тянуть сделку и готовиться к выходу
                                            trigger_take_profit_price_reached = 1
                                            triger_data_dict[orders["open"]["orderId"]]["trigger_take_profit_price_reached"] = trigger_take_profit_price_reached
                                            trigger_take_profit_price = price_bid_1 # новая траггерная цена тейкпрофита
                                            triger_data_dict[orders["open"]["orderId"]]["coin_price_to_sell"] = price_bid_1 # переставляем цену coin_price_to_sell
                                            coin_price_to_sell = price_coin_buyed * (1 + take_profit / 100)
                                            if "trigger_take_profit_price" not in triger_data_dict[orders["open"]["orderId"]]:
                                                triger_data_dict[orders["open"]["orderId"]]["trigger_take_profit_price"] = trigger_take_profit_price
                                            triger_data_dict[orders["open"]["orderId"]]["trigger_take_profit_price"] = trigger_take_profit_price
                                            if admin_module == True:
                                                print(f"достигнута новая триггерная цена на тейкпрофит {price_bid_1}, начальная цена тейкпрофит {start_take_profit_price}")
                                        if triger_data_dict[orders["open"]["orderId"]]["trigger_take_profit_price_reached"] == 1: # цена тейкпрофит достигнута, тянем и готовимся к выходу из сделки
                                            #print("цена выхода")

                                            #print(triger_data_dict[orders["open"]["orderId"]]["trigger_take_profit_price"]*(1-sl_take_ptofit/100))
                                            #if price_bid_1 <= triger_data_dict[orders["open"]["orderId"]]["trigger_take_profit_price"]*(1-sl_take_ptofit/100)+3*float(tickSize) or price_bid_1>=triger_data_dict[orders["open"]["orderId"]]["max_coin_price_to_sell"]: # цена упала ниже чем тейкпрофит уменьшенный на стоплосс тейкпрофита или цена достигла максимального тейкпрофита:
                                            if price_bid_1 <= triger_data_dict[orders["open"]["orderId"]]["trigger_take_profit_price"] * (1 - sl_take_ptofit / 100) or price_bid_1 >=triger_data_dict[orders["open"]["orderId"]]["max_coin_price_to_sell"]:  # цена упала ниже чем тейкпрофит уменьшенный на стоплосс тейкпрофита или цена достигла максимального тейкпрофита:
                                                if admin_module == True:
                                                    print(f"цена упала ниже чем стоплосс от тейкпрофита или достигла максимального тейкпрофита, выходим из сделки. Цена сейчас {price_bid_1}, начальная цена тейкпрофит {start_take_profit_price}")
                                                if plot_make_flag == 1:
                                                    plot_timer = datetime.datetime.now().timestamp()
                                                    plot_orders_data["close_order_price"].append((plot_timer, price_bid_1))
                                                #выставляем лимитный ордер на продажу
                                                # Приведем объем и цену в кратный вид
                                                #coin_price_to_sell = price_bid_1-3*float(tickSize) # по этой цене выходим лимитной заявкаой
                                                coin_price_to_sell = price_bid_1 - price_bid_1 * sl_take_ptofit / 100  # по этой цене выходим лимитной заявкаой
                                                #coin_price_to_sell = triger_data_dict[orders["open"]["orderId"]]["trigger_take_profit_price"]  # по этой цене выходим лимитной заявкаой
                                                # increment_order_price = round(coin_price_to_sell / float(priceIncrement)) * float(priceIncrement)
                                                # increment_order_price = round(increment_order_price, 2)  # округлим цену закупки до центов
                                                increment_order_price = coin_price_to_sell
                                                increment_order_price = round(increment_order_price, len(str(tickSize).split(".")[1]))  # округлим цену закупки прирощения цены
                                                # print(f"{tickSize=}\n{sl_take_ptofit=}\n{coin_price_to_sell=}\n{increment_order_price=}\n{price_bid_1=}\n{coin_price_to_sell=}\n{increment_order_price=}\n")
                                                # определим объем ордера в монетах и приведем его в кратный вид
                                                #order_size = coin_qty_to_sell
                                                order_size = triger_data_dict[orders["open"]["orderId"]]["coin_qty_to_sell"] - triger_data_dict[orders["open"]["orderId"]]["cumExecFee"]
                                                # print(f"{order_size=}")
                                                # TODO рабьота с пылью. Если в сетке был всего один ордер и он закрывается, то продадим весь актив чтобы избавиться от пыли
                                                sell_with_dust = False
                                                if total_orders_in_grid == 1:
                                                    result = check_if_closed_grid_exist(symbol=ticket)
                                                    if result[0] == 0:  # значит файл closed сетки не существует, можем продавать пыль
                                                        if demo_flag !=1:
                                                            if admin_module ==True:
                                                                print("Продаем весь актив, чтобы избавиться от пыли")
                                                            try:
                                                                order_size = float(session.get_wallet_balance(accountType="UNIFIED",coin=ticket.replace("USDT",""),)['result']['list'][0]['coin'][0]['walletBalance'])
                                                                sell_with_dust = True
                                                            except Exception as ex:
                                                                tb_str = traceback.format_exc()
                                                                time_error = datetime.datetime.now()
                                                                # if admin_module == True:
                                                                #     log_text = f"ОШИБКА В main_user_function {time_error}\n{ex}\n{tb_str}\n"
                                                                #     bot.send_message(chat_id="1575144075", message=log_text)
                                                                #     print(f"ОШИБКА при закрытии ордера {time_error}\n{ex}\n{tb_str}\n")
                                                                #     with open('Error_logger.txt', 'a+',encoding='utf-8-sig') as file:
                                                                #         try:
                                                                #             file.write(log_text)
                                                                #         finally:
                                                                #             file.close()
                                                increment_order_size = int(order_size / float(baseIncrement)) * float(baseIncrement)
                                                increment_order_size = round(increment_order_size, len(str(baseIncrement).split(".")[1]))  # еще раз округлим, чтобы убрать 000000000001, округляем на количество знаков после запятой у baseIncrement
                                                # print(len(str(baseIncrement).split(".")[1]))
                                                # print(f"{order_size=},{increment_order_size=}")
                                                try:
                                                    limit_order = limit_order_bybit(session=session, category="spot", symbol=ticket, side="Sell",
                                                                                    qty=str(increment_order_size), price=str(increment_order_price),timeInForce="GTC")
                                                except Exception as ex:
                                                    tb_str = traceback.format_exc()
                                                    time_error = datetime.datetime.now()
                                                    log_file = 'Error_logger.txt'
                                                    limit_order = ex
                                                    try:
                                                        if admin_module:
                                                            tb_str = traceback.format_exc()
                                                            log_text = f"ОШИБКА В limit_order {time_error}\n{ex}\n{tb_str}\n"
                                                            print(
                                                                f"ОШИБКА В limit_order {time_error}\n{ex}\n{tb_str}\n")
                                                        else:
                                                            log_text = f"ОШИБКА В limit_order {time_error}\n{ex}\n"
                                                            print(ex)
                                                        with open(log_file, 'a+', encoding='utf-8-sig') as file:
                                                            file.write(log_text)
                                                    except Exception as e:
                                                        print(f"Не удалось записать в лог-файл: {e}")
                                                if "Insufficient balance" in str(limit_order):
                                                    try:
                                                        message = f"ОШИБКА. Недостаточный баланс при выходе. uid={uid}"
                                                        if demo_flag == 1:
                                                            message += "DEMO!!!"
                                                        bot.send_message(chatid="1575144075", message=message)
                                                    except Exception as ex:
                                                        print(ex)

                                                orderId = limit_order['result']['orderId']
                                                # if admin_module == True:
                                                #     # print(f"{limit_order=}\n{orderId=}")

                                                # order_details = session.get_open_orders(category="spot", orderId=orderId)
                                                attempt = 0
                                                while attempt < max_attempt:
                                                    order_details = session.get_open_orders(category="spot",orderId=orderId)
                                                    retMsg = order_details['retMsg']
                                                    data_order = order_details['result']['list']
                                                    if retMsg == "OK" and data_order != []:
                                                        break
                                                    attempt += 1
                                                    order_details = "NO CORRECT DATA"
                                                    time.sleep(1)
                                                if order_details == "NO CORRECT DATA":
                                                    try:
                                                        message = f"ОШИБКА. При выставлении ордера на закрытие, апи не вернуло order_details. UID = {uid}"
                                                        if demo_flag == 1:
                                                            message += "DEMO!!!"
                                                        bot.send_message(chatid="1575144075", message=message)
                                                    except Exception as ex:
                                                        print(ex)

                                                order_status = order_details['result']['list'][0]["orderStatus"]
                                                # order_price = order_details['result']['list'][0]["price"]

                                                # try:
                                                #     message = f"Close ордер выставлен\nЦена рынка(от апи):{price_bid_1}\nЦена по которой хотим выствить ордер (из данных алгоритма):{coin_price_to_sell}\nЦена по которой выставлен ордер (из данных апи) {order_price}"
                                                #     for chatid in chat_ids:
                                                #         message = message
                                                #         if demo_flag == 1:
                                                #             message += "DEMO!!!"
                                                #         bot.send_message(chatid, message)
                                                # except Exception as ex:
                                                #     print(ex)


                                                # TODO запишем ордер в файл
                                                # открываем файл

                                                ### это удалить после перехода на бд НАЧАЛО
                                                # with open(f"{file_path}", encoding='utf-8-sig') as json_file:
                                                #     orders_data_update = json.load(json_file)
                                                # for i_update in orders_data_update["orders_data"]:
                                                #     index = 0
                                                #     for key_update in i_update.keys():
                                                #         if key_update == key:
                                                #             # print("ордер айди совпал, добавим данные ордера на выход из сделки в словарь")
                                                #             # orders_data_update["orders_data"][index][key_update]["close"] = order_details['result']['list'][0]
                                                #             order_index = 0
                                                #             for order in i_update[key_update]:
                                                #                 if order["open"]["orderId"] == orders["open"]["orderId"]:
                                                #                     #print("нашли нужный ордер, обновляем данные")
                                                #                     orders_data_update["orders_data"][index][key_update][order_index]["close"] = order_details['result']['list'][0]
                                                #                 order_index +=1
                                                #
                                                #     index += 1
                                                # #обновим файл
                                                # with open(f"{file_path}", 'w', encoding='utf-8-sig') as outfile:
                                                #     json.dump(orders_data_update, outfile)
                                                ### это удалить после перехода на бд КОНЕЦ


                                                # Базы данных БД, обновим файл текущей сетки. НАЧАЛО
                                                # прочитаем данные первой сетки из базы
                                                # Базы данных БД, откроем файл orders_data если файл текущей сетки уже существует
                                                result = check_if_open_grid_exist(symbol=ticket)
                                                if result[0] == 1: # значит файл сетки существует
                                                    orders_data = json.loads(result[1]) # прочитаем файл сетки
                                                    # if admin_module == True:
                                                    #     print("БД файл сетки существует. откроем файл")
                                                for i in orders_data["orders_data"]:
                                                    for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                                                        first_order_in_grid = key

                                                orders_data_update = orders_data
                                                for i_update in orders_data_update["orders_data"]:
                                                    index = 0
                                                    for key_update in i_update.keys():
                                                        if key_update == key:
                                                            # print("ордер айди совпал, добавим данные ордера на выход из сделки в словарь")
                                                            # orders_data_update["orders_data"][index][key_update]["close"] = order_details['result']['list'][0]
                                                            order_index = 0
                                                            for order in i_update[key_update]:
                                                                if order["open"]["orderId"] == orders["open"]["orderId"]:
                                                                    #print("нашли нужный ордер, обновляем данные")
                                                                    orders_data_update["orders_data"][index][key_update][order_index]["close"] = order_details['result']['list'][0]
                                                                order_index +=1
                                                # обновим файл текущей сетки
                                                update_open_grid_on_base(first_order_in_grid=first_order_in_grid,update_order_data=orders_data_update)
                                                # Базы данных БД, обновим файл текущей сетки. КОНЕЦ

                                                #endless_cicle_stop = 1
                                                # TODO тут нужно добавить проверку статуса, если ордер заполнен, то только в этом случае close_orders_in_grid_counter +=1
                                                close_orders_in_grid_counter +=1

                                                #TODO ордер сетки закрыт, перезапишем цену на открытие нового ордера, чтобы снова можно было работать в этом диапазоне
                                                #удалим помледний элемент списка, и перезапишем coin_price_to_open_new_order
                                                if len(triger_data_dict[first_grid_order_id]["coin_price_to_open_new_order_list"])>1:
                                                    triger_data_dict[first_grid_order_id]["coin_price_to_open_new_order_list"].pop(-1)
                                                    triger_data_dict[first_grid_order_id]["coin_price_to_open_new_order"] = triger_data_dict[first_grid_order_id]["coin_price_to_open_new_order_list"][-1]
                                                # if "coin_price_to_open_new_order" in triger_data_dict[orders["open"]["orderId"]]:
                                                #     triger_data_dict[first_grid_order_id]["coin_price_to_open_new_order"] = triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order"]  # переставляем цену coin_price_to_open_new_order в главном ордере сетки
                                                # print("ордер сетки закрыт, перезапишем цену на открытие нового ордера, чтобы сново можно было работать в этом диапазоне")

                                                # если ордер заполнился мгновенно, то отправим сообщение о закрытом ордере пользователю
                                                if order_status == "Filled":
                                                    cumExecValue = float(order_details['result']['list'][0]["cumExecValue"])
                                                    cumExecFee = float(order_details['result']['list'][0]["cumExecFee"])
                                                    usdt_qty_to_buy_coin = float(orders["open"]['cumExecValue'])


                                                    profit = cumExecValue - cumExecFee - usdt_qty_to_buy_coin
                                                    profit_percent = round(profit / usdt_qty_to_buy_coin * 100, 2)

                                                    #print(f"{profit=}")
                                                    try:
                                                        #message = f"profit={round(profit, 3)}"
                                                        for chatid in chat_ids:
                                                            if user_bot_name == "":
                                                                user_bot_name = "CRYPTO BULL"
                                                            message = f"💵 {round(profit, 3)}$ | {profit_percent}% \u25B2 {ticket} {user_bot_name}"
                                                            if demo_flag == 1:
                                                                message += "DEMO!!!"
                                                            if sell_with_dust == True:
                                                                message += " + крипто пыль."
                                                            bot.send_message(chatid, message)
                                                            with lock:
                                                                is_new_message_to_tg_was_sent = True
                                                    except Exception as ex:
                                                        print(ex)

                                                #TODO если open был частично исполнен, то отменим его
                                                if orders["open"]["orderStatus"] == "PartiallyFilled":
                                                    # отменим ордер по апи
                                                    order_id_to_dell = orders["open"]["orderId"]
                                                    cancel_order = session.cancel_order(category="spot", symbol=ticket,orderId=order_id_to_dell)

                                    else :
                                        #print(f"Для {order_id=} уже выставлен close order, пропускаем его")
                                        close_orders_in_grid_counter += 1

                                #############################
                                # УСЛОВИЯ ДЛЯ ОТКРЫТИЯ НОВОГО ОРДЕРА С МУЛЬТИПЛИКАТОРОМ
                                #############################
                                try:
                                    # if len(triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order_list"]) > 1:
                                    #     triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order"] = triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order_list"][-1]
                                    # НОВЫЕ ОРДЕРА ОТКРЫВАЕМ ТОЛЬКО РАБОТАЯ С ПЕРВЫМ ОРДЕРОМ В СЕТКЕ
                                    if is_it_first_grid_order == 1 and is_order_status_filled == 1 and total_open_orders_in_grid<2*max_order_qty: # новое для сеток длины 2х добавляем 2*
                                        # print(f'coin_price_to_open_new_order={triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order"]}')
                                        #TODO для меня делаю так, чтобы новые ордера не открывались, если включена сушка
                                        if uid == "130602840" and sushka_mode == True:
                                            price_ask_1 = 99999999

                                        if price_ask_1 <= triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order"]: # открываем новый ордер с мультипликатором
                                            if admin_module == True:
                                                print("Цена упала до уровня открытия нового ордера с мультипликатором")
                                            if plot_make_flag == 1:
                                                plot_timer = datetime.datetime.now().timestamp()
                                                plot_orders_data["grid_step_triger"].append((plot_timer, price_ask_1))
                                            # если цена еще упала - переносим coin_price_to_open_new_order ниже
                                            #trigger_take_profit_price_reached = 1
                                            # trigger_take_profit_price = price_bid_1  # новая траггерная цена открытия нового ордера
                                            # coin_price_to_sell = price_bid_1  # переставляем цену coin_price_to_sell
                                            #coin_price_to_open_new_order = price_ask_1 * (1 - prise_down_to_open_new_order / 100) # переставляем цену coin_price_to_open_new_order
                                            # TODO наверное лучше сделать так чтобы coin_price_to_open_new_order расчитывалась как степень от количества открытых ордеров в строке 479, а здесь уже ничего не обновлять, но это если при падении цены не нужно переставлять coin_price_to_open_new_order
                                            #coin_price_to_open_new_order = price_ask_1 # переставляем цену coin_price_to_open_new_order
                                            #coin_price_to_open_new_order = price_ask_1 * (1-grid_step*grid_multiplikator**total_open_orders_in_grid/100) # переставляем цену coin_price_to_open_new_order
                                            #triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order"] = coin_price_to_open_new_order
                                            # print(f"{is_new_coin_price_to_open_new_order_added=}")
                                            # if is_new_coin_price_to_open_new_order_added == 0:
                                            #     coin_price_to_open_new_order = price_ask_1 * (1 - grid_step * grid_multiplikator ** total_open_orders_in_grid / 100)  # переставляем цену coin_price_to_open_new_order
                                            #     triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order"] = coin_price_to_open_new_order
                                            #     triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order_list"].append(coin_price_to_open_new_order)
                                            #     is_new_coin_price_to_open_new_order_added = 1 # поднимаем флаг того что добавлен новый шаг сетки
                                            # else:
                                            #     coin_price_to_open_new_order = price_ask_1 # переставляем цену coin_price_to_open_new_order
                                            #     triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order"] = coin_price_to_open_new_order
                                            triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order"] = price_ask_1 # перезапишем coin_price_to_open_new_order
                                            triger_data_dict[orders["open"]["orderId"]]["is_price_down_to_open_new_grid_order"] = 1 # поднимаем флаг - Цена упала до уровня открытия нового ордера с мультипликатором
                                            #TODO если new_order_amount определять таким образом, то не будет геометрической прогрессии в размере новых ордеров в сетке
                                            #TODO определим new_order_amount, он будет увеличиваться в геометрической прогрессии
                                            #new_order_amount = triger_data_dict[orders["open"]["orderId"]]["min_order_amount"] * multiplikator
                                            new_order_amount = min_order_amount * multiplikator**total_open_orders_in_grid
                                            if new_order_amount > max_order_amount: # условие чтобы размер ордера не был больше чем максимально допустимый
                                                new_order_amount = max_order_amount
                                            triger_data_dict[orders["open"]["orderId"]]["min_order_amount"] = new_order_amount # обновляем стартовый объем на закупку
                                            start_order_price = price_ask_1 * (1 + trall_tp / 100)  # определим цену по которой будем входить и приведем ее в кратный вид
                                            if admin_module == True:
                                                # print(f"{price_ask_1=}")
                                                # print(f"{trall_tp=}")
                                                # print(f"{start_order_price=}")
                                                print(f"достигнута новая триггерная цена цена открытия нового ордера {coin_price_to_open_new_order}, начальная цена открытия нового ордера {start_coin_price_to_open_new_order}")





                                        # если флаг is_price_down_to_open_new_grid_order поднят, то готовимся открыть новый ордер на покупку в сетке, если цена поднимется на тралл входа
                                        if "is_price_down_to_open_new_grid_order" in triger_data_dict[orders["open"]["orderId"]]:
                                            if triger_data_dict[orders["open"]["orderId"]]["is_price_down_to_open_new_grid_order"]==1:
                                                # print(f'is_price_down_to_open_new_grid_order={triger_data_dict[orders["open"]["orderId"]]["is_price_down_to_open_new_grid_order"]}')
                                                #TODO тут ошибка ордера открываются раньше времени, должна быть цена >= start_order_price а не coin_price_to_open_new_order
                                                #if price_ask_1 >= triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order"] * (1 + trall_tp / 100) - 3*float(tickSize):
                                                if price_ask_1 >= start_order_price:
                                                    if admin_module == True:
                                                        print(f'цена выросла на чем трал ТП от нового grid_step, входим в нову сделку в сетке. Цена сейчас {price_bid_1}, начальная цена шага сетки {triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order"]}')
                                                    if plot_make_flag == 1:
                                                        plot_timer = datetime.datetime.now().timestamp()
                                                        plot_orders_data["open_order_price"].append((plot_timer, price_ask_1))
                                                    # выставляем лимитный ордер на покупку
                                                    # расчитаем объем и цену и приведем в кратный вид
                                                    #start_order_price = triger_data_dict[orders["open"]["orderId"]]["coin_price_to_open_new_order"] * (1 + trall_tp / 100)  # определим цену по которой будем входить и приведем ее в кратный вид
                                                    #start_order_price = price_ask_1  # определим цену по которой будем входить и приведем ее в кратный вид
                                                    start_order_price = price_ask_1 + price_ask_1 * sl_take_ptofit / 100  # определим цену по которой будем входить и приведем ее в кратный вид
                                                    #increment_start_order_price = round(start_order_price / float(priceIncrement)) * float(priceIncrement)
                                                    increment_start_order_price = start_order_price
                                                    increment_start_order_price = round(increment_start_order_price, len(str(tickSize).split(".")[1]))  # округлим цену закупки до tickSize
                                                    # определим объем ордера в монетах и приведем его в кратный вид
                                                    start_order_size = new_order_amount / start_order_price
                                                    increment_start_order_size = round(start_order_size / float(baseIncrement)) * float(baseIncrement)
                                                    increment_start_order_size = round(increment_start_order_size, len(str(baseIncrement).split(".")[1]))  # еще раз округлим, чтобы убрать 000000000001, округляем на количество знаков после запятой у baseIncrement
                                                    #print(f"{start_order_price=},{increment_start_order_price=}")
                                                    #print(f"{start_order_size=},{increment_start_order_size=}")
                                                    timer_5 = datetime.datetime.now().timestamp()
                                                    # выставляем лимитный ордер на покупку и закрываем цикл поиска точки входа в первый ордер сетки и выставления ордера на вход
                                                    try:
                                                        limit_order = limit_order_bybit(session=session, category="spot",
                                                                                        symbol=ticket,
                                                                                        side="Buy",
                                                                                        qty=str(increment_start_order_size),
                                                                                        price=str(increment_start_order_price),
                                                                                        timeInForce="GTC")
                                                    except Exception as ex:
                                                        tb_str = traceback.format_exc()
                                                        time_error = datetime.datetime.now()
                                                        log_file = 'Error_logger.txt'
                                                        limit_order = ex
                                                        try:
                                                            if admin_module:
                                                                tb_str = traceback.format_exc()
                                                                log_text = f"ОШИБКА В limit_order {time_error}\n{ex}\n{tb_str}\n"
                                                                print(
                                                                    f"ОШИБКА В limit_order {time_error}\n{ex}\n{tb_str}\n")
                                                            else:
                                                                log_text = f"ОШИБКА В limit_order {time_error}\n{ex}\n"
                                                                print(ex)
                                                            with open(log_file, 'a+', encoding='utf-8-sig') as file:
                                                                file.write(log_text)
                                                        except Exception as e:
                                                            print(f"Не удалось записать в лог-файл: {e}")
                                                    orderId = limit_order['result']['orderId']
                                                    # if admin_module == True:
                                                    #     print(f"{limit_order=}\n{orderId=}")
                                                    #     print(f"время от взятия стакана до открытия ордера {timer_5-timer_4}")

                                                    # получаем данные по ордеру
                                                    # order_details = session.get_open_orders(category="spot", orderId=orderId)
                                                    attempt = 0
                                                    while attempt < max_attempt:
                                                        order_details = session.get_open_orders(category="spot",
                                                                                                orderId=orderId)
                                                        retMsg = order_details['retMsg']
                                                        data_order = order_details['result']['list']
                                                        if retMsg == "OK" and data_order != []:
                                                            break
                                                        attempt += 1
                                                        order_details = "NO CORRECT DATA"
                                                        time.sleep(1)
                                                    if order_details == "NO CORRECT DATA":
                                                        try:
                                                            message = f"ОШИБКА. При выставлении ордера на открытие, апи не вернуло order_details. UID = {uid}"
                                                            if demo_flag == 1:
                                                                message += "DEMO!!!"
                                                            bot.send_message(chatid="1575144075", message=message)
                                                        except Exception as ex:
                                                            print(ex)

                                                    #price_coin_buyed = float(order_details['result']['list'][0]['avgPrice'])
                                                    # следующий шаг сетки
                                                    grid_step_price = price_ask_1 * (1-grid_step*grid_multiplikator**total_open_orders_in_grid/100) # переставляем цену coin_price_to_open_new_order

                                                    # новое для работы с сетками длины 2х
                                                    if total_open_orders_in_grid > max_order_qty:
                                                        # price_of_max_order_qty_order = triger_data_dict[first_order_id_in_grid]["coin_price_to_open_new_order_list"][max_order_qty] # цена по которой должен открываться последний ордер из max_order_qty сетки
                                                        # coin_price_to_open_new_order = price_of_max_order_qty_order * (1 - (additional_grid_fall_percent/max_order_qty) * (total_open_orders_in_grid-max_order_qty+1) / 100)
                                                        # coin_price_to_open_new_order = triger_data_dict[first_order_id_in_grid]["coin_price_to_open_new_order_list"][total_open_orders_in_grid-1] * (1 - (additional_grid_fall_percent/max_order_qty) / 100)
                                                        # coin_price_to_open_new_order = triger_data_dict[first_order_id_in_grid]["coin_price_to_open_new_order_list"][-1] * (1 - (additional_grid_fall_percent / max_order_qty) / 100)
                                                        grid_step_price = price_ask_1 * (1 - (additional_grid_fall_percent / max_order_qty) / 100) # переставляем цену coin_price_to_open_new_order

                                                    # добавим coin_price_to_open_new_order в данные по ордеру, чтобы потом открывать новые ордера в этом шаге сетки
                                                    if orderId not in triger_data_dict:
                                                        triger_data_dict[orderId] = {}
                                                    if "coin_price_to_open_new_order" not in triger_data_dict[orderId]:
                                                        triger_data_dict[orderId]["coin_price_to_open_new_order"] = grid_step_price
                                                    triger_data_dict[first_grid_order_id]["coin_price_to_open_new_order"] = grid_step_price
                                                    triger_data_dict[first_grid_order_id]["coin_price_to_open_new_order_list"].append(grid_step_price)
                                                    #print(triger_data_dict)
                                                    # сохраним данные нового ордера в сетке
                                                    # запишем новый ордер в файл

                                                    ### удилить после перехода на бд. начало
                                                    # # открываем файл
                                                    # with open(f"{file_path}", encoding='utf-8-sig') as json_file:
                                                    #     orders_data_update = json.load(json_file)
                                                    # for i_update in orders_data_update["orders_data"]:
                                                    #     index = 0
                                                    #     for key_update in i_update.keys():
                                                    #         if key_update == key:
                                                    #             if admin_module == True:
                                                    #                 print("ордер айди совпал, добавим данные нового ордера на вход с мультипликатором")
                                                    #             orders_data_update["orders_data"][index][key_update].append({"open": order_details['result']['list'][0]})
                                                    #     index += 1
                                                    # # обновим файл
                                                    # with open(f"{file_path}", 'w', encoding='utf-8-sig') as outfile:
                                                    #     json.dump(orders_data_update, outfile)
                                                    ### удилить после перехода на бд. начало

                                                    # Базы данных БД, обновим файл текущей сетки. НАЧАЛО
                                                    # прочитаем данные первой сетки из базы
                                                    # Базы данных БД, откроем файл orders_data если файл текущей сетки уже существует
                                                    result = check_if_open_grid_exist(symbol=ticket)
                                                    if result[0] == 1:  # значит файл сетки существует
                                                        orders_data = json.loads(result[1])  # прочитаем файл сетки
                                                        # if admin_module == True:
                                                        #     print("БД файл сетки существует. откроем файл")
                                                    for i in orders_data["orders_data"]:
                                                        for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                                                            first_order_in_grid = key

                                                    orders_data_update = orders_data
                                                    for i_update in orders_data_update["orders_data"]:
                                                        index = 0
                                                        for key_update in i_update.keys():
                                                            if key_update == key:
                                                                # if admin_module == True:
                                                                #     print("ордер айди совпал, добавим данные нового ордера на вход с мультипликатором")
                                                                orders_data_update["orders_data"][index][key_update].append({"open": order_details['result']['list'][0]})
                                                        index += 1
                                                    # обновим файл текущей сетки
                                                    # print(f"{first_order_in_grid=}")
                                                    # print(f"{orders_data_update=}")
                                                    update_open_grid_on_base(first_order_in_grid=first_order_in_grid,
                                                                             update_order_data=orders_data_update)
                                                    # Базы данных БД, обновим файл текущей сетки. КОНЕЦ


                                                    triger_data_dict[orders["open"]["orderId"]]["is_price_down_to_open_new_grid_order"] = 0  # опускаем флаг - Цена упала до уровня открытия нового ордера с мультипликатором
                                                    is_new_coin_price_to_open_new_order_added = 0 # опускаем флаг
                                                    #TODO вот тут поидее надо откатить цену открытия нового ордера до начального уровня предидущего ордера????
                                                    # откуда отсчитывать новыую цену открытия нового ордера
                                except Exception as ex:
                                    tb_str = traceback.format_exc()
                                    time_error = datetime.datetime.now()
                                    log_file = 'Error_logger.txt'
                                    limit_order = ex
                                    try:
                                        if admin_module:
                                            tb_str = traceback.format_exc()
                                            log_text = f"ОШИБКА во время открытия нового ордера {time_error}\n{ex}\n{tb_str}\n"
                                            print(
                                                f"ОШИБКА во время открытия нового ордера {time_error}\n{ex}\n{tb_str}\n")
                                        else:
                                            log_text = f"ОШИБКА во время открытия нового ордера {time_error}\n{ex}\n"
                                            print(ex)
                                        with open(log_file, 'a+', encoding='utf-8-sig') as file:
                                            file.write(log_text)
                                    except Exception as e:
                                        print(f"Не удалось записать в лог-файл: {e}")

                            # TODO шаг сетки будем определять как шаг на котором был открыт последний открытый ордер сетки, это для того чтобы работать в диапазоне сразу за последний открытым ордером
                            # print("len(list(triger_data_dict.keys()))")
                            # print(len(list(triger_data_dict.keys())))
                            # print(f"{triger_data_dict=}")
                            # if len(list(triger_data_dict.keys())) > 1:
                            #     if "coin_price_to_open_new_order" in triger_data_dict[orders["open"]["orderId"]]:
                            #         if orders["open"]["orderId"] in triger_data_dict and last_open_order_id in triger_data_dict:
                            #             if last_open_order_id == first_grid_order_id:
                            #                 triger_data_dict[first_grid_order_id]['coin_price_to_open_new_order'] = triger_data_dict[last_open_order_id]['start_coin_price_to_open_new_order']
                            #             else:
                            #                 triger_data_dict[first_grid_order_id]['coin_price_to_open_new_order'] = triger_data_dict[last_open_order_id]['coin_price_to_open_new_order']
                            #             print(f'определили шаг сетки coin_price_to_open_new_order={triger_data_dict[first_grid_order_id]["coin_price_to_open_new_order"]}, {last_open_order_id=}')

                            #TODO проверка, если последний ордер сетки со статусом new,а все остальные уже закрылись, то отменим этот ордер и удалим его из сетки
                            #################################
                            # ПРОВЕРКА, если последний ордер сетки со статусом new,а все остальные уже закрылись, то отменим этот ордер и удалим его из сетки. НАЧАЛО
                            #################################
                            # откроем файл orders_data
                            # file_path = 'orders_data/orders_data.txt'

                            # ### удалить после перехода на бд НАЧАЛО
                            # if os.path.exists(file_path):  # если файл с сетками ордеров уже создан, прочитаем его
                            #     with open(f"{file_path}", encoding='utf-8-sig') as json_file:
                            #         orders_data = json.load(json_file)
                            # ### удалить после перехода на бд КОНЕЦ

                            #TODO раскоментировать после перехода на БД

                            # Базы данных БД, откроем файл текущей сетки.
                            # прочитаем данные первой сетки из базы
                            # Базы данных БД, откроем файл orders_data если файл текущей сетки уже существует
                            result = check_if_open_grid_exist(symbol=ticket)
                            if result[0] == 1:  # значит файл сетки существует
                                orders_data = json.loads(result[1])  # прочитаем файл сетки
                                # if admin_module == True:
                                #     print("БД файл сетки существует. откроем файл")
                            for i in orders_data["orders_data"]:
                                for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                                    first_order_in_grid = key

                            # идем по orders_data и обновляем статусы всех наших ордеров из сеток в соответствии со списком open_orders
                            for i in orders_data["orders_data"]:  # i - это сетка ордеров, вохможно их будет несколько, возможно одна
                                index = 0
                                for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                                    # print(f"{key=}")
                                    first_grid_order_id = key
                                    orders_index = 0
                                    order_complete_list = []
                                    for orders in i[
                                        key]:  # i[key] это все ордера сетки, в том числе и первый, orders - это словарь с данными {open:..., close:...}
                                        # print(orders)
                                        if "open" in orders and "close" in orders:
                                            #print(f"ордер сетки номер {orders_index} исполнен")
                                            order_complete_list.append({orders["open"]["orderId"]: "complete"})
                                        else:
                                            if orders["open"]["orderStatus"] == "New" or orders["open"]["orderStatus"] == "Cancelled":
                                                #print(f"ордер сетки номер {orders_index} не исполнен или отменен")
                                                order_complete_list.append({orders["open"]["orderId"]: "new"})
                                            else:
                                                #print(f"ордер сетки номер {orders_index}")
                                                order_complete_list.append({orders["open"]["orderId"]: "unknown"})
                                        orders_index += 1
                                    # print(order_complete_list)
                                    # for key in order_complete_dict:
                                    is_all_orders_except_last_complete = 0
                                    counter = 0
                                    mutch_counter = len(order_complete_list[0:-1])
                                    for i in order_complete_list[0:-1]:
                                        # print(i.values())
                                        for key in i:
                                            if i[key] == "complete":
                                                counter += 1
                                    if counter == mutch_counter:
                                        is_all_orders_except_last_complete = 1
                                    # print(f"{mutch_counter=}, {counter=}")
                                    # print(is_all_orders_except_last_complete)
                                    is_last_order_status_new = 0
                                    for key in order_complete_list[-1]:
                                        if order_complete_list[-1][key] == "new":
                                            is_last_order_status_new = 1
                                            order_id_to_dell = key
                                    #print(is_last_order_status_new)
                                    if is_last_order_status_new == 1 and is_all_orders_except_last_complete == 1:
                                        if admin_module == True:
                                            print("вся сетка закрыта кроме последнего ордера, последний ордер со статусом new, удалим его и закроем сетку")
                                        #print(orders_index - 1)
                                        # удалим ордер из файла сетки
                                        orders_data["orders_data"][index][first_grid_order_id].pop(orders_index - 1)
                                        # # обновим файл
                                        # with open(f"{file_path}", 'w', encoding='utf-8-sig') as outfile:
                                        #     json.dump(orders_data, outfile)

                                        # Базы данных БД, обновим файл текущей сетки
                                        update_open_grid_on_base(first_order_in_grid=first_order_in_grid, update_order_data=orders_data)

                                        # отменим ордер по апи
                                        cancel_order = session.cancel_order(category="spot", symbol=ticket,
                                                                            orderId=order_id_to_dell)
                                        #print(cancel_order)
                                index += 1

                            #################################
                            # ПРОВЕРКА, РАСЧЕТ ПРИБЫЛЬНОСТИ СЕТКИ, и проверка, если сетка долго открыта и прибыль по уже закрытым ордерам больше чем 2х от убытков по еще открытым ордерам, то закрываем сетку по рынку
                            #################################
                            timer_profit_count_1 = datetime.datetime.now().timestamp()
                            current_price = price_bid_1
                            total_grid_profit_counter = 0
                            grid_profit_counter = 0
                            grid_loss_counter = 0
                            orders_to_close_list = []  # это список открытых ордеров, которые нужно закрыть, чтобы закрыть сетку, если прибыль по остальным достаточна
                            stop_timer = datetime.datetime.now().timestamp()
                            #print(f"Общее время работы сетки {int(stop_timer - start_time_of_grid)}")
                            if close_order_3x_process_started == False:
                                if stop_timer - start_time_of_grid > min_working_time_of_grid or total_open_orders_in_grid_counter >= 6: # если прошло мин время работы сетки
                                    # Базы данных БД, откроем файл orders_data если файл текущей сетки уже существует
                                    result = check_if_open_grid_exist(symbol=ticket)
                                    if result[0] == 1:  # значит файл сетки существует
                                        orders_data = json.loads(result[1])  # прочитаем файл сетки
                                    # идем по orders_data и обновляем статусы всех наших ордеров из сеток в соответствии со списком open_orders
                                    for i in orders_data["orders_data"]:  # i - это сетка ордеров, вохможно их будет несколько, возможно одна
                                        index = 0
                                        for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                                            orders_index = 0
                                            order_complete_list = []
                                            for orders in i[
                                                key]:  # i[key] это все ордера сетки, в том числе и первый, orders - это словарь с данными {open:..., close:...}
                                                # print(f"{orders=}")
                                                if "open" in orders and "close" in orders:
                                                    #print('этот ордер закрыт')
                                                    if orders["close"]["orderStatus"] == "Filled":
                                                        #print(orders)
                                                        # расчитаем прибыль
                                                        #print(float(orders["close"]["cumExecValue"]),float(orders["close"]["cumExecFee"]),float(orders["open"]["cumExecValue"]))
                                                        profit = float(orders["close"]["cumExecValue"]) - float(
                                                            orders["close"]["cumExecFee"]) - float(orders["open"]["cumExecValue"])
                                                        #print(f"{profit=}")
                                                        # total_crypto_bull_profit_counter += profit
                                                        total_grid_profit_counter += profit
                                                        grid_profit_counter += profit
                                                        # if orders["open"]["orderId"] not in profit_messege_send_list:
                                                        #     message = f"profit={round(profit,3)}"
                                                        #     bot.send_message("1575144075", message)
                                                        #     profit_messege_send_list.append(orders["open"]["orderId"])
                                                    else: # ордер не исполнен, расчитаем прибыль по открытому ордеру
                                                        loss = current_price * (float(orders["open"]["cumExecQty"]) - float(
                                                            orders["open"]["cumExecFee"])) - float(orders["open"]["cumExecValue"])
                                                        # print(f"{loss=}")
                                                        # total_crypto_bull_profit_counter += loss
                                                        total_grid_profit_counter += loss
                                                        grid_loss_counter += loss

                                                elif "open" in orders and "close" not in orders:
                                                    #print('этот ордер еще открыт')
                                                    #print(orders["open"])
                                                    # расчитаем убыток, если закрыться сейчас
                                                    loss = current_price * (float(orders["open"]["cumExecQty"]) - float(
                                                        orders["open"]["cumExecFee"])) - float(orders["open"]["cumExecValue"])
                                                    #print(f"{loss=}")
                                                    # total_crypto_bull_profit_counter += loss
                                                    total_grid_profit_counter += loss
                                                    grid_loss_counter += loss
                                                    orders_to_close_list.append(orders["open"])
                                                    # if orders["open"]["orderId"] not in profit_messege_send_list:
                                                    #     message = f"{loss=}"
                                                    #     bot.send_message("1575144075", message)
                                                    #     profit_messege_send_list.append(orders["open"]["orderId"])
                                        # print(orders)
                                    #print(f"{total_grid_profit_counter=}")
                                    timer_profit_count_2 = datetime.datetime.now().timestamp()
                                    # print(f"Время Расчета прибыльности сетки {timer_profit_count_2-timer_profit_count_1}")
                                    # print(f"{grid_profit_counter=}")
                                    # print(f"{grid_loss_counter=}")


                                    # if abs(grid_profit_counter) > 0.01 * abs(grid_loss_counter) and grid_loss_counter != 0:

                                    if abs(grid_profit_counter) > profit_loss_ratio_to_close_grig * abs(grid_loss_counter) and grid_loss_counter != 0:
                                        close_order_3x_process_started = True
                                        coin_price_to_sell_3x_event = price_bid_1
                                        if plot_make_flag == 1:
                                            plot_timer = datetime.datetime.now().timestamp()
                                            plot_orders_data["tp_close_triger"].append((plot_timer, price_ask_1))
                                        if admin_module == True:
                                            print(f"прибыль больше чем 3х от потерь, можно закрывать открытые ордера")
                                            print(f"Тянем выход по 3х {ticket}")
                                        try:
                                            if admin_module == True:
                                                for chatid in chat_ids:
                                                    if user_bot_name == "":
                                                        user_bot_name = "CRYPTO BULL"
                                                    message = f"{ticket} Прибыль больше 3х от потерь, закрываем сетку {user_bot_name}."
                                                    if demo_flag == 1:
                                                        message += "DEMO!!!"
                                                    bot.send_message(chatid,message)
                                                    with lock:
                                                        is_new_message_to_tg_was_sent = True
                                        except Exception as ex:
                                            print(ex)

                            if close_order_3x_process_started == True:
                                # print(f"{total_orders_in_grid=}")
                                # print(f"{close_orders_in_grid_counter=}")
                                if price_bid_1 > coin_price_to_sell_3x_event:
                                    coin_price_to_sell_3x_event = price_bid_1 # передвигаем цену coin_price_to_sell_3x_event
                                    if admin_module == True:
                                        print(f"достигнута новая триггерная цена на тейкпрофит coin_price_to_sell_3x_event = {price_bid_1}")
                                    if plot_make_flag == 1:
                                        plot_timer = datetime.datetime.now().timestamp()
                                        plot_orders_data["tp_close_triger"].append((plot_timer, price_ask_1))

                                if price_bid_1 <= coin_price_to_sell_3x_event * (1 - sl_take_ptofit / 100):  # цена упала ниже чем тейкпрофит уменьшенный на стоплосс тейкпрофита или цена достигла максимального тейкпрофита:
                                    if admin_module == True:
                                        print(f"цена упала ниже чем стоплосс от тейкпрофита, выходим по 3х. coin_price_to_sell_3x_event {price_bid_1}")
                                    if plot_make_flag == 1:
                                        plot_timer = datetime.datetime.now().timestamp()
                                        plot_orders_data["close_order_price"].append((plot_timer, price_bid_1))
                                    # закроем открытые ордера по рынку
                                    #print(orders_to_close_list)
                                    # идем по orders_data и составим список ордеров которые нужно закрыть
                                    # Базы данных БД, откроем файл orders_data если файл текущей сетки уже существует
                                    result = check_if_open_grid_exist(symbol=ticket)
                                    if result[0] == 1:  # значит файл сетки существует
                                        orders_data = json.loads(result[1])  # прочитаем файл сетки
                                        # if admin_module == True:
                                        #     print("БД файл сетки существует. откроем файл")
                                    for i in orders_data["orders_data"]:  # i - это сетка ордеров, вохможно их будет несколько, возможно одна
                                        index = 0
                                        for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                                            orders_index = 0
                                            order_complete_list = []
                                            for orders in i[key]:  # i[key] это все ордера сетки, в том числе и первый, orders - это словарь с данными {open:..., close:...}
                                                if "open" in orders and "close" not in orders:
                                                    orders_to_close_list.append(orders["open"])
                                    print(f"{orders_to_close_list=}")
                                    for i in orders_to_close_list:
                                        #print(i)
                                        if plot_make_flag == 1:
                                            plot_timer = datetime.datetime.now().timestamp()
                                            plot_orders_data["close_order_price"].append((plot_timer, price_bid_1))
                                        # выставляем ордер на продажу
                                        # выставляем лимитный ордер на продажу
                                        order_id = i["orderId"]
                                        # Приведем объем и цену в кратный вид
                                        # coin_price_to_sell = price_bid_1  # по этой цене выходим лимитной заявкаой
                                        coin_price_to_sell = price_bid_1 - price_bid_1 * sl_take_ptofit / 100  # по этой цене выходим лимитной заявкаой
                                        # increment_order_price = round(coin_price_to_sell / float(priceIncrement)) * float(
                                        #     priceIncrement)
                                        # increment_order_price = round(increment_order_price,2)  # округлим цену закупки до центов
                                        increment_order_price = coin_price_to_sell
                                        increment_order_price = round(increment_order_price, len(str(tickSize).split(".")[1]))  # округлим цену закупки прирощения цены

                                        #print(f"{coin_price_to_sell=},{increment_order_price=}")
                                        # определим объем ордера в монетах и приведем его в кратный вид
                                        # order_size = coin_qty_to_sell
                                        order_size = triger_data_dict[order_id]["coin_qty_to_sell"] - triger_data_dict[order_id]["cumExecFee"]
                                        increment_order_size = int(order_size / float(baseIncrement)) * float(baseIncrement)
                                        increment_order_size = round(increment_order_size, len(str(baseIncrement).split(".")[1]))  # еще раз округлим, чтобы убрать 000000000001, округляем на количество знаков после запятой у baseIncrement
                                        #print(len(str(baseIncrement).split(".")[1]))
                                        #print(f"{order_size=},{increment_order_size=}")
                                        try:
                                            limit_order = limit_order_bybit(session=session, category="spot", symbol=ticket,
                                                                            side="Sell",
                                                                            qty=str(increment_order_size),
                                                                            price=str(increment_order_price), timeInForce="GTC")
                                        except Exception as ex:
                                            tb_str = traceback.format_exc()
                                            time_error = datetime.datetime.now()
                                            log_file = 'Error_logger.txt'
                                            limit_order = ex
                                            try:
                                                if admin_module:
                                                    tb_str = traceback.format_exc()
                                                    log_text = f"ОШИБКА В limit_order {time_error}\n{ex}\n{tb_str}\n"
                                                    print(f"ОШИБКА В limit_order {time_error}\n{ex}\n{tb_str}\n")
                                                else:
                                                    log_text = f"ОШИБКА В limit_order {time_error}\n{ex}\n"
                                                    print(ex)
                                                with open(log_file, 'a+', encoding='utf-8-sig') as file:
                                                    file.write(log_text)
                                            except Exception as e:
                                                print(f"Не удалось записать в лог-файл: {e}")
                                        if "Insufficient balance" in str(limit_order):
                                            try:
                                                message = f"ОШИБКА. Недостаточный баланс при выходе 3х. uid={uid}"
                                                if demo_flag == 1:
                                                    message += "DEMO!!!"
                                                bot.send_message(chatid="1575144075", message=message)
                                            except Exception as ex:
                                                print(ex)

                                        orderId = limit_order['result']['orderId']
                                        if admin_module == True:
                                            print(f"{limit_order=}\n{orderId=}")
                                        # order_details = session.get_open_orders(category="spot", orderId=orderId)
                                        attempt = 0
                                        while attempt < max_attempt:
                                            order_details = session.get_open_orders(category="spot",
                                                                                    orderId=orderId)
                                            retMsg = order_details['retMsg']
                                            data_order = order_details['result']['list']
                                            if retMsg == "OK" and data_order != []:
                                                break
                                            attempt += 1
                                            order_details = "NO CORRECT DATA"
                                            time.sleep(1)
                                        if order_details == "NO CORRECT DATA":
                                            try:
                                                message = f"ОШИБКА. При выставлении ордера на закрытие 3х, апи не вернуло order_details. UID = {uid}"
                                                if demo_flag == 1:
                                                    message += "DEMO!!!"
                                                bot.send_message(chatid="1575144075", message=message)
                                            except Exception as ex:
                                                print(ex)
                                        order_status = order_details['result']['list'][0]["orderStatus"]
                                        # TODO запишем ордер в файл
                                        # # открываем файл
                                        # with open(f"{file_path}", encoding='utf-8-sig') as json_file:
                                        #     orders_data_update = json.load(json_file)


                                        # Базы данных БД, откроем файл текущей сетки.
                                        # прочитаем данные первой сетки из базы
                                        # Базы данных БД, откроем файл orders_data если файл текущей сетки уже существует
                                        result = check_if_open_grid_exist(symbol=ticket)
                                        if result[0] == 1:  # значит файл сетки существует
                                            orders_data = json.loads(result[1])  # прочитаем файл сетки
                                            # if admin_module == True:
                                            #     print("БД файл сетки существует. откроем файл")
                                            orders_data_update = orders_data
                                        for i in orders_data["orders_data"]:
                                            for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                                                first_order_in_grid = key


                                        for i_update in orders_data_update["orders_data"]:
                                            index = 0
                                            for key_update in i_update.keys():
                                                if key_update == key:
                                                    # print("ордер айди совпал, добавим данные ордера на выход из сделки в словарь")
                                                    # orders_data_update["orders_data"][index][key_update]["close"] = order_details['result']['list'][0]
                                                    order_index = 0
                                                    for order in i_update[key_update]:
                                                        if order["open"]["orderId"] == order_id:
                                                            #print("нашли нужный ордер, обновляем данные")
                                                            orders_data_update["orders_data"][index][key_update][order_index]["close"] = order_details['result']['list'][0]
                                                        order_index += 1

                                            index += 1
                                            # # обновим файл
                                            # with open(f"{file_path}", 'w', encoding='utf-8-sig') as outfile:
                                            #     json.dump(orders_data_update, outfile)

                                            # Базы данных БД, обновим файл текущей сетки
                                            update_open_grid_on_base(first_order_in_grid=first_order_in_grid,
                                                                     update_order_data=orders_data_update)

                                        # endless_cicle_stop = 1
                                        # TODO тут нужно добавить проверку статуса, если ордер заполнен, то только в этом случае close_orders_in_grid_counter +=1
                                        close_orders_in_grid_counter += 1


                            #################################
                            # ПРОВЕРКА, если последний ордер сетки со статусом new,а все остальные уже закрылись, то отменим этот ордер и удалим его из сетки. КОНЕЦ
                            #################################


                            #################################
                            # ПРОВЕРКА полного закрытия сетки и сборка сообщения в консоль. НАЧАЛО
                            #################################
                            #TODO условие полного закрытия сетки - если количество закрыт
                            time_in_grid = str(round((stop_timer - start_time_of_grid) / 3600, 2))
                            hours = time_in_grid.split(".")[0]
                            minutes = int(float(f"0.{time_in_grid.split('.')[1]}") * 60)
                            if admin_module == True:
                                console_message = "#" * 40
                                console_message += f"\n{'-'*40}"
                                console_message += f"\nТекущая пара:       {ticket}"
                                console_message += f"\nМинимальный ордер:  {min_order_amount}"
                                #if demo_flag ==1:
                                console_message += f"\nНачальная цена:     {price_coin_buyed_start_order}"
                                console_message += f"\nТекущая цена:       {price_bid_1}"
                                console_message += f"\n{'-' * 40}"
                                console_message += f"\nВремя в сетке:      {hours}ч{minutes}мин"
                                console_message += f"\n{'-' * 40}"
                                console_message += f"\nВсего открыто ордеров в сетке: {total_orders_in_grid}"
                                console_message += f"\nВсего закрыто ордеров в сетке: {close_orders_in_grid_counter}"
                                console_message += f"\n{'-' * 40}"
                                # console_message += f"\nОткрыто ордеров:     {total_orders_in_grid-close_orders_in_grid_counter} из {max_order_qty}"
                                if sushka_mode == True:
                                    console_message += f"\nРежим сушки ВКЛ"
                                if persent_mode == True:
                                    console_message += f"\nАвторазгон ВКЛ"
                                else:
                                    console_message += f"\nАвторазгон ВЫКЛ"
                                if exp_flag == 1:
                                    console_message += f"\nПОДПИСКА НЕ АКТИВНА!!!"
                                console_message += f"\n{'#'*40}"
                                if socket_flag ==0:
                                    console_message += f"\nНет связи с сокетом!!!"

                                svodkda_massage = f"{ticket} | {min_order_amount} usdt | {total_orders_in_grid - close_orders_in_grid_counter}/{max_order_qty}"

                            else:
                                console_message = "#" * 40
                                console_message += f"\n{'-' * 40}"
                                console_message += f"\nТекущая пара:       {ticket}"
                                console_message += f"\nМинимальный ордер:  {min_order_amount}"
                                console_message += f"\n{'-' * 40}"
                                console_message += f"\nВремя в сетке:      {hours}ч{minutes}мин"
                                console_message += f"\n{'-' * 40}"
                                console_message += f"\nОткрыто ордеров:     {total_orders_in_grid - close_orders_in_grid_counter} из {max_order_qty}"
                                if sushka_mode == True:
                                    console_message += f"\nРежим сушки ВКЛ"
                                if persent_mode == True:
                                    console_message += f"\nАвторазгон ВКЛ"
                                else:
                                    console_message += f"\nАвторазгон ВЫКЛ"
                                if exp_flag == 1:
                                    console_message += f"\nПОДПИСКА НЕ АКТИВНА!!!"
                                console_message += f"\n{'#' * 40}"

                                svodkda_massage = f"{ticket} | {min_order_amount} usdt | {total_orders_in_grid - close_orders_in_grid_counter}/{max_order_qty}"

                            # print(f"{triger_data_dict=}")
                            #print(f"{total_orders_in_grid=}\n{close_orders_in_grid_counter=}")

                            if datetime.datetime.now().timestamp() - console_message_timer > 10:
                                # console_message = "#"*40
                                # console_message += f"\n{'-'*40}"
                                # console_message +=f"\nТекущая пара:       {ticket}"
                                # if demo_flag ==1:
                                #     console_message += f"\nНачальная цена:     {price_coin_buyed_start_order}"
                                #     console_message += f"\nТекущая цена:       {price_bid_1}"
                                # console_message += f"\n{'-' * 40}"
                                # console_message += f"\nВремя в сетке:      {hours}ч{minutes}мин"
                                # console_message += f"\n{'-' * 40}"
                                # console_message += f"\nВсего открыто ордеров в сетке: {total_orders_in_grid}"
                                # console_message += f"\nВсего закрыто ордеров в сетке: {close_orders_in_grid_counter}"
                                # console_message += f"\n{'-' * 40}"
                                # console_message += f"\nОткрыто ордеров:     {total_orders_in_grid-close_orders_in_grid_counter} из {max_order_qty}"

                                # console_message += f"\n{'#'*40}"
                                print(console_message)
                                ts = time.time()
                                console_message_dict = {"message": console_message, "ts": ts, "svodkda_massage": svodkda_massage}
                                with lock:
                                    if ticket not in total_console_message_dict:
                                        total_console_message_dict[ticket] = {}
                                with lock:
                                    total_console_message_dict[ticket] = console_message_dict


                                if admin_module == True:
                                    # print(f"{triger_data_dict=}")
                                    if first_order_id_in_grid in triger_data_dict:
                                        if "coin_price_to_open_new_order_list" in triger_data_dict[first_order_id_in_grid]:
                                            print(f"Шаги сетки {triger_data_dict[first_order_id_in_grid]['coin_price_to_open_new_order_list']}")
                                console_message_timer = datetime.datetime.now().timestamp()


                            if total_orders_in_grid == close_orders_in_grid_counter:
                                if admin_module == True:
                                    print(f"Все ордера сетки закрыты! {ticket}")
                                endless_cicle_stop = 1
                                # переместим файл с сеткой в папку с завершенными сетками
                                # PATH = 'closed_grid'
                                # if not os.path.exists(PATH):
                                #     os.makedirs(PATH)
                                timestump = str(datetime.datetime.now().timestamp())
                                # os.replace("orders_data/orders_data.txt", "closed_grid/orders_data.txt")
                                # os.rename("closed_grid/orders_data.txt", f"closed_grid/{timestump}.txt")

                                # Базы данных БД. переместим файл с сеткой из open grid в closed_grid
                                transfer_grid_from_open_to_closed(first_order_in_grid=first_order_in_grid)

                                #########################
                                # условие для закрытия потока
                                #########################
                                if endless_cicle_stop == 1 and sushka_mode == True:
                                    sushka_completed_stop_thread = 1
                                    print(f"СУШКА завершена, закрываем алгоритм для {ticket}")
                                    try:
                                        # message = f"profit={round(profit, 3)}"
                                        for chatid in chat_ids:
                                            if user_bot_name == "":
                                                user_bot_name = "CRYPTO BULL"
                                            message = f"СУШКА ЗАВЕРШЕНА! {ticket} {user_bot_name}"
                                            if demo_flag == 1:
                                                message += "DEMO!!!"
                                            bot.send_message(chatid, message)
                                            with lock:
                                                is_new_message_to_tg_was_sent = True
                                    except Exception as ex:
                                        print(ex)
                                    # завершаем поток
                                    with lock:
                                        thread_started_dict[ticket] = False # отмечаем в словаре. что потока с этой монетой нет
                                    # # TODO если монета пользовательская, то в словаре user_coin_names нужно поменять имя на USER COIN user_coin_names={'user_coin_1': 'asd', 'user_coin_2': 'solusdt', 'user_coin_3': 'USER COIN'}
                                    # with lock:
                                    #     if ticket.lower() in user_coin_names.values():
                                    #         if admin_module == True:
                                    #             print("СУШКА завершена, пользовательская монета, поменяем название на USER COIN")
                                    #         for key_coin in user_coin_names.keys():
                                    #             if user_coin_names[key_coin] == ticket.lower():
                                    #                 user_coin_names[key_coin] = 'USER COIN'
                                    # нужно удалить записи из БД в столбцах настроек монеты и настроек сушки
                                    with sq.connect("crypto_bull.db") as con:
                                        try:
                                            cur = con.cursor()
                                            # проверим если ли запись в бд
                                            cur.execute("""
                                                            SELECT user_api_key, user_api_secret, user_chat_id,user_symbol_list, sushka_mode_list
                                                            FROM actually_user_settings
                                                        """)
                                            result = cur.fetchone()
                                            user_symbol_list = json.loads(result[3])
                                            sushka_mode_list = json.loads(result[4])
                                            # print(user_symbol_list, sushka_mode_list)
                                            update_user_symbol_list = {}
                                            update_sushka_mode_list = {}
                                            for key in user_symbol_list:
                                                if key != ticket.lower():
                                                    update_user_symbol_list[key] = user_symbol_list[key]
                                            for key in sushka_mode_list:
                                                if key != ticket.lower():
                                                    update_sushka_mode_list[key] = sushka_mode_list[key]
                                            # print(update_user_symbol_list)
                                            # print(update_sushka_mode_list)

                                            # обновим данные в БД
                                            update_user_symbol_list = json.dumps(
                                                update_user_symbol_list)  # Преобразуем словарь в строку JSON
                                            update_sushka_mode_list = json.dumps(update_sushka_mode_list)
                                            # изменяем данные в столбце
                                            try:
                                                cur = con.cursor()
                                                cur.execute("""
                                                                    UPDATE actually_user_settings 
                                                                    SET user_symbol_list = ?, sushka_mode_list = ?
                                                                    WHERE user_api_key = ?
                                                                """, (update_user_symbol_list, update_sushka_mode_list,
                                                                      result[0]))  # Параметризованный запрос
                                                con.commit()  # сохраним изменения
                                            except Exception as e:
                                                print(f"Ошибка при обновлении данных: {e}")


                                        except Exception as e:
                                            print(f"Ошибка при чтении данных: {e}")





                                # TODO отправим визуализацию сетки админам
                                if admin_module == True:
                                    start_time_point = plot_orders_data['ask_price'][0][0]  # начальное значение таймштамп для нормализации оси х
                                    total_grid_time = (plot_orders_data['ask_price'][-1][0]) - (plot_orders_data['ask_price'][0][0])
                                    #print(f"{total_grid_time=}")
                                    ratio_to_plot_small_lines = 25

                                    # простоим график ask_price
                                    if len(plot_orders_data['ask_price']) > 0:
                                        x_side_1 = []
                                        y_side_1 = []
                                        for i in plot_orders_data['ask_price']:
                                            x_side_1.append(i[0] - start_time_point)
                                            y_side_1.append(i[1])
                                        plt.plot(x_side_1, y_side_1, color='#000000', label="coin_price")
                                    # нанесем stat_price
                                    if len(plot_orders_data['stat_price']) > 0:
                                        index = 0
                                        for i in plot_orders_data['stat_price']:
                                            price_open_point_x = i[0] - start_time_point
                                            price_open_point_y = i[1]
                                            if index == 0:
                                                plt.plot(price_open_point_x, price_open_point_y, 'o', color="#000000",
                                                         label='start_price/price_update')
                                            # elif index == 1:
                                            #     plt.plot(price_open_point_x, price_open_point_y, 'o', color="#D2691E", label='start_price_update')
                                            else:
                                                # plt.plot(price_open_point_x, price_open_point_y, 'o', color="#D2691E")
                                                plt.plot(price_open_point_x, price_open_point_y, 'o', color="#000000")
                                            index += 1
                                        plt.plot(plot_orders_data['stat_price'][0][0] - start_time_point,
                                                 plot_orders_data['stat_price'][0][1], 'o', color="#000000")
                                    # нанесем шаги сетки
                                    if len(plot_orders_data['grid_step_triger']) > 0:
                                        index = 0
                                        for i in plot_orders_data['grid_step_triger']:
                                            x_side_1 = (i[0] - start_time_point - total_grid_time / ratio_to_plot_small_lines,
                                                        i[0] - start_time_point + total_grid_time / ratio_to_plot_small_lines)
                                            y_side_1 = (i[1], i[1])
                                            if index == 0:
                                                x_side_1 = (
                                                i[0] - start_time_point - total_grid_time / ratio_to_plot_small_lines,
                                                i[0] - start_time_point + total_grid_time / ratio_to_plot_small_lines)
                                                y_side_1 = (i[1], i[1])
                                                plt.plot(x_side_1, y_side_1, color='#800080', label="grid_step/step_update")
                                            # elif index == 1:
                                            #     plt.plot(x_side_1, y_side_1, color='#800000', label="grid_step_update")
                                            else:
                                                # plt.plot(x_side_1, y_side_1, color='#800000')
                                                plt.plot(x_side_1, y_side_1, color='#800080')
                                            index += 1
                                    # нанесем точки открытия ордеров
                                    if len(plot_orders_data['open_order_price']) > 0:
                                        index = 0
                                        for i in plot_orders_data['open_order_price']:
                                            price_open_point_x = i[0] - start_time_point
                                            price_open_point_y = i[1]
                                            if index == 0:
                                                plt.plot(price_open_point_x, price_open_point_y, 'o', color="g",
                                                         label='open_price')
                                            else:
                                                plt.plot(price_open_point_x, price_open_point_y, 'o', color="g")
                                            index += 1
                                    # нанесем шаги TP
                                    if len(plot_orders_data['tp_close_triger']) > 0:
                                        index = 0
                                        for i in plot_orders_data['tp_close_triger']:
                                            x_side_1 = (i[0] - start_time_point - total_grid_time / ratio_to_plot_small_lines,
                                                        i[0] - start_time_point + total_grid_time / ratio_to_plot_small_lines)
                                            y_side_1 = (i[1], i[1])
                                            if index == 0:
                                                x_side_1 = (
                                                i[0] - start_time_point - total_grid_time / ratio_to_plot_small_lines,
                                                i[0] - start_time_point + total_grid_time / ratio_to_plot_small_lines)
                                                y_side_1 = (i[1], i[1])
                                                plt.plot(x_side_1, y_side_1, color='g', label="TP_price/price_update")
                                            # elif index == 1:
                                            #     plt.plot(x_side_1, y_side_1, color='g', label="TP_price_update")
                                            else:
                                                plt.plot(x_side_1, y_side_1, color='g')
                                            index += 1

                                    # нанесем точки закрытия ордеров
                                    if len(plot_orders_data['close_order_price']) > 0:
                                        index = 0
                                        for i in plot_orders_data['close_order_price']:
                                            price_open_point_x = i[0] - start_time_point
                                            price_open_point_y = i[1]
                                            if index == 0:
                                                plt.plot(price_open_point_x, price_open_point_y, 'o', color="r",
                                                         label='close_price')
                                            else:
                                                plt.plot(price_open_point_x, price_open_point_y, 'o', color="r")
                                            index += 1

                                    plt.xlabel("Время,сек")
                                    plt.ylabel("Цена,USDT")
                                    # plt.legend()
                                    plt.grid(True)
                                    plt.savefig(f'1.jpg')
                                    plt.close()




                                    # plt.show()
                                    for chatid in chat_ids:
                                        #print(chatid)
                                        # создаем буфер, сохраняем график в буфер, перемещаем указатель на начало буфера
                                        buf = io.BytesIO()
                                        plt.savefig(buf, format="png")
                                        buf.seek(0)
                                        caption = f"{console_message}\nПрибыль за сетку: {round(total_grid_profit_counter,2)}"
                                        if demo_flag == 1:
                                            caption += "\nDEMO!!!"
                                        #bot.send_photo(chat_id=chatid, photo=buf, caption=caption)
                                        try:
                                            bot.send_photo(chat_id=chatid, photo=open(f'1.jpg', 'rb'), caption=caption)
                                            with lock:
                                                is_new_message_to_tg_was_sent = True
                                            #print(f"Сообщение отправлено {chatid=}, {caption=}")
                                        except Exception as ex:
                                            print(ex)
                                        #time.sleep(0.25)

                                #сохраним данные для построения графико
                                if plot_make_flag == 1:
                                    PATH = 'orders_data/plot_orders_data'
                                    if not os.path.exists(PATH):
                                        os.makedirs(PATH)
                                    file_path = f'orders_data/plot_orders_data/{timestump}.txt'
                                    with open(f"{file_path}", 'w', encoding='utf-8-sig') as outfile:
                                        json.dump(plot_orders_data, outfile)

                                print("Поиск новой точки входа.")
                                time.sleep(sleep_time)  # сон после завершенной сетки
                                #TODO здсь запускаем цикл в котором будем проверять не заполненные ордера закрытых сеток поштучно.
                                # также здесь нужно разово проыерить активна ли подписка по времени
                    timer_endless_cicle_end = time.time()
            except Exception as ex:
                tb_str = traceback.format_exc()
                time_error = datetime.datetime.now()
                # if admin_module == True:
                #     log_text = f"ОШИБКА В main_user_function {time_error}\n{ex}\n{tb_str}\n"
                #     print(f"ОШИБКА В main_user_function {time_error}\n{ex}\n{tb_str}\n")
                #     with open('Error_logger.txt', 'a+', encoding='utf-8-sig') as file:
                #         try:
                #             file.write(log_text)
                #         finally:
                #             file.close()
                # else:
                #     log_text = f"ОШИБКА В main_user_function {time_error}\n{ex}\n"
                #     with open('Error_logger.txt', 'a+', encoding='utf-8-sig') as file:
                #         try:
                #             file.write(log_text)
                #         finally:
                #             file.close()
                #     print(ex)

                log_file = 'Error_logger.txt'
                max_log_size = 10 * 1024 * 1024  # 10MB
                target_log_size = 5 * 1024 * 1024  # 5MB

                try:
                    # Проверяем размер файла
                    if os.path.exists(log_file) and os.path.getsize(log_file) > max_log_size:
                        # Если файл больше 10MB, обрезаем его до 10MB, сохраняя последние записи
                        with open(log_file,
                                  'rb+') as file:  # Открываем в бинарном режиме для корректной работы с размером
                            file_size = os.path.getsize(log_file)
                            bytes_to_keep = min(target_log_size, file_size)
                            file.seek(bytes_to_keep, os.SEEK_SET)
                            file.truncate()  # Обрезаем файл с текущей позиции
                            file.seek(0, os.SEEK_SET)  # Переходим в начало файла

                    time_error = datetime.datetime.now()
                    if admin_module:
                        tb_str = traceback.format_exc()
                        log_text = f"ОШИБКА В ESM_CRYPTO_BULL {time_error}\n{ex}\n{tb_str}\n"
                        print(f"ОШИБКА В ESM_CRYPTO_BULL {time_error}\n{ex}\n{tb_str}\n")
                    else:
                        log_text = f"ОШИБКА В ESM_CRYPTO_BULL {time_error}\n{ex}\n"
                        print(ex)

                    with open(log_file, 'a+', encoding='utf-8-sig') as file:
                        file.write(log_text)

                except Exception as e:
                    print(f"Не удалось записать в лог-файл: {e}")
                time.sleep(7)





if __name__ == "__main__":
    #####################
    # ВВОДИМ ИСХОДНЫЕ ДАННЫЕ ПОДПИСКИ. НАЧАЛО
    #####################
    '''
    #########################################################################
    # Прописываем uid пользователя, который будет жестко привязан к этой версии програмы
    #########################################################################
    '''
    uid = "136500935"  # Вводим uid который указал пользователь. Админы "41085914" "130602840"
    '''
    #########################################################################
    # установим дату окончания работы алгоритма - для версии по подписке
    #########################################################################
    '''
    exp_date = "15.09.2025 00:33:00" # вводим дату окончания подписки, в формате "27.04.2025 7:45:00"
    '''
    #########################################################################
    # установим флаг если пользователь купил полную версию алгоритма
    #########################################################################
    '''
    full_pack_flag = True # True - если пользователь купил полную версию, False - если подписку
    #####################
    # ВВОДИМ ИСХОДНЫЕ ДАННЫЕ ПОДПИСКИ. КОНЕЦ
    #####################



    if full_pack_flag == True:
        exp_time = 9747325220 # если пользователь купил полную версии, то у него бесконечная подписка
    elif full_pack_flag == False:
        # переведем дату в timestump
        format_string = "%d.%m.%Y %H:%M:%S"
        datetime_object = datetime.datetime.strptime(exp_date, format_string)
        exp_time = time.mktime(datetime_object.timetuple())

        # exp_time = 1747325220  # подписка истекает 15 мая 2025


    print(f"{exp_time=}")
    #########################################################################
    #########################################################################
    bot_name = "Cripto_arb_bot"
    tele_bot_token = "6775042853:AAGspQVuoUUUgtRr-hBeru1VBaaNYRajJAI"
    bot_name = "ESM_Monitoring_bot"
    tele_bot_token = "7991371365:AAGz3UUHqdki8ZMAw4R20hJQiIefjsJGdVc"
    bot = telebot.TeleBot(tele_bot_token)  # создаем объект бот

    # Глобальные переменные для сокетов
    MAX_PRICES = 100 # соклько значений current price храним в списке
    lock = threading.Lock()
    stop_event_socket = threading.Event()  # событие для остановки потока сокетов
    price_dict = {} # словарь с ценами монет от сокета

    # список монет с которыми работает алгоритм и основные флаги
    # working_ticket_list = ["BTCUSDT","ETHUSDT", "XRPUSDT","LINKUSDT","TONUSDT","DOTUSDT"]
    # ALLOWED_COINS = ["btcusdt", "xrpusdt", "ethusdt", "linkusdt", "tonusdt", "dotusdt"] # для кнопок
    allowed_coins = ["btcusdt", "xrpusdt", "ethusdt", "linkusdt", "tonusdt", "dotusdt", "bnbusdt", "solusdt", "ltcusdt", "dogeusdt", "arbusdt", "mntusdt"]
    max_selected_coins = 10  # Максимум можно выбрать 10 монет
    used_dinamic_take_profit = True # флаг используем ли динамический тейк профит, который расчитывается для каждой монеты в зависимости от размера пыли, мин ордера, СЛТП итд
    if uid == "130602840":
        used_dinamic_take_profit = False
        print(f"{used_dinamic_take_profit=}")

    used_enter_in_grid_just_after_grid_closed = False # флаг входим сразу после завершения сетки, так же он отменяет слип 120 секунд после окончания сетки
    if uid == "130602840":
        used_enter_in_grid_just_after_grid_closed = False

    stop_event = threading.Event() # событие для остановки всех потоков при выключении интерфейса




    #глобальные переменные для графического интерфейса
    shushka_buttons = {}
    shushka_mode = {}
    USER_COIN_PREFIX = "user_coin_"  # Префикс для пользовательских монет
    NUM_USER_COINS = 10  # Количество пользовательских монет
    user_coins = [f"{USER_COIN_PREFIX}{i + 1}" for i in range(NUM_USER_COINS)]
    user_coin_names = {coin: "USER COIN" for coin in user_coins}  # Изначально названия одинаков

    threads = [] # список с потоками алгоритмов
    threads_dict = {} # словарь с потоками алгоритмов
    threads_socket_dict = {} # словарь с потоками сокетов
    total_console_message_dict = {} # словарь для формирования общего сообщения и для контроля работы потоков по времени обновления сообщения
    messages = [] # словарь для хранения сообщений для терминалаи блокировки доступа к ней
    lock = threading.Lock()  # создаем замок для управления общими данными из потоков

    try:
        # создаем базу данных, если она еще не создана
        create_database()
        # импортируем данные сеток из папок
        # if os.path.exists('orders_data') or os.path.exists('closed_grid'):
        #     import_orders_data_from_folders_to_base()

        # запуск графического интерфейса
        # run_gui()
        # Создаем и запускаем поток для графического интерфейса
        gui_thread = threading.Thread(target=run_gui, args=())
        gui_thread.start()

        # запуск системы безопасности и интерфейса
        security_check_data = security_check_and_console_interface()

        # читаем настройки монет пользователя из базы и запускаем алгоритмы
        start_check_user_coin_settings_time = 0
        is_socket_price_started = False  # флаг запущен ли поток с сокетами
        current_symbol_list_for_socket = []
        thread_started_dict = {}  # словарь в который записываем какие потоки с какими монетами уже запущены
        user_coin_settings_dict = {}
        is_new_message_to_tg_was_sent = False # флаг автосводки
        while stop_event.is_set() == False:
        # while 1==1:
        #     print(f"стоп событие {stop_event.is_set()}")
            # if stop_event.is_set() == True: # если стоп событие установлено (закрыт интерфейс программы)
            #     print("ИНТЕРФЕЙС ЗАКРЫТ, ПРЕРЫВАЕМ РАБОТУ АЛГОРИТМА!")

            # прочитаем пользовательские настройки из базы
            # print(f"время дельта {time.time() - start_check_user_coin_settings_time}")
            try:
                if time.time() - start_check_user_coin_settings_time >15: # проверяем настройки пользователя каждые 15 сек
                    # print(f"{total_console_message_dict=}")
                    total_message_to_print_in_interface = ""
                    for key in total_console_message_dict:
                        total_message_to_print_in_interface += total_console_message_dict[key]["message"] + "\n"
                        if time.time() - float(total_console_message_dict[key]["ts"]) > 120 and key.lower() in user_coin_settings_dict: # словарь не обновлялся из потока более 60 сек
                            total_message_to_print_in_interface = f"!!! ПОТЕРЯНА СВЯЗЬ С АЛГОРИТМОМ {key.upper()} !!!"
                    total_message_to_print_in_interface += f"Время обновления данных {datetime.datetime.now().time().strftime('%H:%M:%S')}"
                    # print(f"{total_message_to_print_in_interface=}")
                    messages.append(total_message_to_print_in_interface)
                    with sq.connect("crypto_bull.db") as con:
                        try:
                            cur = con.cursor()
                            # проверим если ли запись в бд
                            cur.execute("""
                                                SELECT user_symbol_list, sushka_mode_list, user_bot_name, user_api_key, user_api_secret
                                                FROM actually_user_settings
                                            """)
                            result = cur.fetchone()
                            # print(result)
                            if result[0] == None:  # значит поля с настройками еще нет, запишем новые настройки
                                print("Ожидаем ввода настроек монет пользователем.")
                            else:  # значит поле уже есть, обновим данные
                                # print("Пользователь ввел начальные данные по монетам.")
                                # print("Запускаем работу алгоритма.")
                                if uid == "130602840":
                                    print(f"Настройки монет:{result}")
                        except Exception as e:
                            print(f"Ошибка при чтении данных: {e}")
                    start_check_user_coin_settings_time = time.time()
                    # идем по настройкам монет и запускаем потоки с алгоритмом
                    user_coin_settings_dict = json.loads(result[0])
                    user_sushka_settings_dict = json.loads(result[1])
                    user_bot_name = result[2] # имя бота для автосводки монитора
                    user_api_key = result[3]
                    user_api_secret = result[4]
                    # запускаем поток с сокетами
                    if stop_event_socket.is_set() == True: # если был включен стоп ивент, то на следующем шаге скидываем стоп ивент сокета, чтобы он перезапустился
                        stop_event_socket.clear()
                    symbol_list = []  # список монет, на которые нам нужны сокеты
                    for key in user_coin_settings_dict:
                        symbol_list.append(key.upper())
                    # print(f"{symbol_list=}")
                    for symbol in symbol_list: # добавляем монеты в словарь с ценами
                        if symbol not in price_dict:
                            price_dict[symbol] = deque(maxlen=MAX_PRICES)  # список с ограниченным количеством значений
                    # запуск сокета с ценами в отдельном потоке

                    if is_socket_price_started == False and symbol_list != []:
                        thread = threading.Thread(target=socket_current_prices,args=(symbol_list, stop_event,stop_event_socket,lock))  # Создаем поток
                        thread.start()  # Запускаем поток
                        is_socket_price_started = True
                        threads_socket_dict["price_socket"] = thread
                        threads.append(thread)
                        current_symbol_list_for_socket = symbol_list # текущий список символов для сокета с ценами

                    if symbol_list != current_symbol_list_for_socket:
                        print("СОКЕТ настройки изменились, перезапустим поток сокета с ценами")
                        stop_event_socket.set() # включаем стоп событие, чтобы закрыть старый поток с сокетом
                        is_socket_price_started = False # меняем флаг, чтобы запустился новый поток с сокетом

                    if "price_socket" in threads_socket_dict:
                        if threads_socket_dict["price_socket"].is_alive() == False:  # значит поток умер, его нужно перезапустить и обновить словарь threads_dict и список потоков threads
                            print(f"price_socket поток УМЕР")
                            with lock:
                                price_dict = {} # обнуляем словарь с ценами
                                is_socket_price_started = False  # отмечаем что потока с сокетом нет, чтобы он перезапустился

                    if uid == "130602840":
                        print(f"Контроль потоков {threads=}\n{threads_dict=}\n{threads_socket_dict=}")
                        for key in threads_dict:
                            # print(f"{key} поток жив: {threads_dict[key].is_alive()}")
                            #TODO значит поток умер, его нужно перезапустить и обновить словарь threads_dict и список потоков threads
                            # проверить что после сукшки ключ с монетой удаляется из словаря threads_dict
                            if threads_dict[key].is_alive() == False and key.lower() in user_coin_settings_dict: # значит поток умер, его нужно перезапустить и обновить словарь threads_dict и список потоков threads
                                print(f"{key} поток УМЕР")
                                with lock:
                                    thread_started_dict[key] = False  # отмечаем в словаре. что потока с этой монетой нет, чтобы он перезапустился
                        print("КОНТРОЛЬ сообщений из потоков")
                        for key in total_console_message_dict:
                            print(f"{key}, {total_console_message_dict[key]['ts']}, time_delta {round(time.time()-total_console_message_dict[key]['ts'],0)}")
                            print(f"{key}, svodkda_massage: {total_console_message_dict[key]['svodkda_massage']}")
                        # print(f"{thread_started_dict=}")
                        # for thread in threads:
                        #     print(thread.is_alive())
                    for key in user_coin_settings_dict:
                        # print(f"{user_coin_settings_dict=}")
                        # соберем начальные данные для запуска алгоритма
                        demo_flag = security_check_data[0]
                        security_check_flag = security_check_data[1]
                        exp_check_flag = security_check_data[2]
                        admin_module = security_check_data[3]
                        chat_ids = security_check_data[4]
                        session = security_check_data[5]
                        ticket = key.upper()
                        sushka_mode = user_sushka_settings_dict[key]
                        # print(f"{ticket=},{sushka_mode=}")
                        preset_dict = coin_strategy(ticket)
                        min_order_amount = float(user_coin_settings_dict[key]["amount"])
                        persent_mode = user_coin_settings_dict[key]["percent_mode"]

                        start_data = (demo_flag,security_check_flag,exp_check_flag,ticket,admin_module,chat_ids,preset_dict,session,min_order_amount,persent_mode)

                        if ticket not in thread_started_dict:
                            with lock:
                                thread_started_dict[ticket] = False
                        if thread_started_dict[ticket] == False: # если поток для этой монеты еще не запуцен
                            print(f"Запускаем алгоритм для {ticket}")
                            with lock:
                                thread_started_dict[ticket] = True
                            # # запуск торгового алгоритма в отдельном потоке
                            # esm_crypto_bul_thread = threading.Thread(target=esm_crypto_bul, args=(start_data,))
                            # esm_crypto_bul_thread.start()

                            # запуск торгового алгоритма в отдельном потоке
                            thread = threading.Thread(target=esm_crypto_bul, args=(start_data,thread_started_dict,stop_event,user_coin_names, user_bot_name, used_dinamic_take_profit,admin_module,uid, used_enter_in_grid_just_after_grid_closed))  # Создаем поток
                            threads.append(thread)
                            threads_dict[ticket] = thread

                            thread.start()  # Запускаем поток

                            # TODO в потоке алгоритма нужно каждые несколько секунд считывать из базы состояние режима сушки,
                            # когда работа алгоритма завершится после сушки нужно убить поток и поменять флаг thread_started_dict[ticket] = True на  False
                            # и удалить записи из БД в столбцах настроек монеты и настроек сушки
                            # проработать режим percent_mode
                            # добаить проверки во время ввода данных пользователем


                    #TODO такой вариант закрытия потоков не подходит, из-за этого программа ждет завершения потоков,
                    # и не работает цикл while 1==1: и пользовательские настройки считываются только один раз после старта работы программы

                    # for thread in threads:
                    #     thread.join()  # Ждем завершения каждого потока
                    #     threads.remove(thread) # удалим поток из списка

                    #TODO отправляем автосводку, раз в 60 сек
                    if admin_module == True or admin_module == False:
                        # svoka_message_id = "" # id сообщения со сводкой для автообновлений
                        total_svodka_message = ""
                        # ОПРЕДЕЛИМ ВРЕМЯ ПО МОСКВЕ
                        # Определяем часовой пояс Москвы
                        moscow_timezone = pytz.timezone('Europe/Moscow')
                        # Получаем текущее время в UTC
                        utc_now = datetime.datetime.utcnow()
                        # Преобразуем время в московский часовой пояс
                        moscow_now = utc_now.replace(tzinfo=datetime.timezone.utc).astimezone(moscow_timezone)
                        # Форматируем время в нужный формат
                        time_now = moscow_now.time().strftime("%H:%M:%S")
                        # time_now = datetime.datetime.now().time().strftime("%H:%M:%S")
                        bot_name = user_bot_name
                        if bot_name == None or bot_name == "":
                            bot_name = "CRYPTO BULL"
                        # расчитаем баланс
                        svodka_equity = "н/д"
                        svodka_balance = "н/д"
                        today_protit = "н/д"
                        # определим эквити
                        if demo_flag == 1:
                            session = HTTP(api_key=user_api_key, api_secret=user_api_secret)
                        svodka_equity = float(session.get_wallet_balance(accountType="UNIFIED", )['result']['list'][0]['totalEquity'])
                        svodka_equity = round(svodka_equity,2)
                        # определим сводобное количество usdt
                        free_usdt_qty = float(session.get_wallet_balance(accountType="UNIFIED",coin="USDT",)['result']['list'][0]['coin'][0]['walletBalance'])
                        free_usdt_qty = round(free_usdt_qty, 2)

                        # определим баланс
                        # определим количество usdt которое было использовано в открытых ордерах сеток
                        def get_usdt_qty_from_all_open_grids():
                            # функция прочесть данные всех текущех сеток
                            try:
                                with sq.connect("crypto_bull.db") as con:
                                    cur = con.cursor()
                                    cur.execute("SELECT * FROM open_grid")  # Выбираем все строки
                                    data = cur.fetchall()
                                    total_usdt_used_in_grid_counter = 0
                                    if data:
                                        for grid in data:
                                            orders_data = json.loads(grid[2])
                                            for i in orders_data[
                                                "orders_data"]:  # i - это сетка ордеров, вохможно их будет несколько, возможно одна
                                                for key in i.keys():  # key это айди первого ордера в сетке, по сути это ключ к сетке
                                                    for orders in i[key]:
                                                        if "open" in orders and "close" not in orders:
                                                            # print(orders)
                                                            total_usdt_used_in_grid_counter += float(
                                                                orders["open"]['cumExecValue'])

                                    if total_usdt_used_in_grid_counter:
                                        return total_usdt_used_in_grid_counter
                                    else:
                                        return None

                            except sq.Error as e:
                                print(f"Ошибка при получении данных из таблицы open_grid: {e}")
                                return None

                            return total_usdt_used_in_grid_counter

                        total_usdt_used_in_grid = get_usdt_qty_from_all_open_grids()
                        if total_usdt_used_in_grid == None:
                            total_usdt_used_in_grid = 0
                        svodka_balance = free_usdt_qty + total_usdt_used_in_grid
                        svodka_balance = round(svodka_balance,2)


                        # print(f"{svodka_equity=}")
                        #Today profit: {today_protit}
                        total_svodka_message = f"{bot_name}  | \u231A {time_now}\nBalance:      {svodka_balance} usdt\nEquity:         {svodka_equity} usdt\nFree USDT:  {free_usdt_qty} usdt\n\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014"
                        for key in total_console_message_dict:
                            if time.time() - float(total_console_message_dict[key]["ts"]) > 120 and key.lower() in user_coin_settings_dict:  # словарь не обновлялся из потока более 60 сек
                                total_svodka_message += f"\n!!! ПОТЕРЯНА СВЯЗЬ С АЛГОРИТМОМ {key.upper()} !!!"
                            else:
                                # print(f"{key}, svodkda_massage: {total_console_message_dict[key]['svodkda_massage']}")
                                total_svodka_message+=f"\n\u2714{total_console_message_dict[key]['svodkda_massage']}"

                        # отпарвляем сводку первый раз
                        # if svoka_message_id == "":
                        if 'svoka_message_id' not in locals():
                            svodka_message_timer = time.time()
                            try:
                                # message = f"profit={round(profit, 3)}"
                                for chatid in chat_ids:
                                    message = total_svodka_message
                                    if demo_flag == 1:
                                        message += "DEMO!!!"
                                    new_message  = bot.send_message(chatid, message,disable_notification=True)
                                    svoka_message_id = new_message.message_id
                                    # print(f"{svoka_message_id=}")
                            except Exception as ex:
                                print(ex)
                        # удалим старое сообщение и переотправим его:
                        # print(f"{is_new_message_to_tg_was_sent=}")
                        if is_new_message_to_tg_was_sent == True:
                            try:
                                # message = f"profit={round(profit, 3)}"
                                for chatid in chat_ids:
                                    bot.delete_message(chat_id=chatid,message_id=svoka_message_id)
                                    # отпарвим новое сообщение
                                    message = total_svodka_message
                                    if demo_flag == 1:
                                        message += "DEMO!!!"
                                    new_message = bot.send_message(chatid, message, disable_notification=True)
                                    svoka_message_id = new_message.message_id
                                    is_new_message_to_tg_was_sent = False  # меняем флаг нового сообщения обратно
                            except Exception as ex:
                                print(ex)

                        # обновляем сообщение каждые 60 сек
                        svodka_update_time = 15
                        if uid == "130602840":
                            svodka_update_time = 60
                        if time.time() - svodka_message_timer > svodka_update_time:
                            try:
                                # message = f"profit={round(profit, 3)}"
                                for chatid in chat_ids:
                                    bot.edit_message_text(
                                                            chat_id=chatid,
                                                            message_id=svoka_message_id,
                                                            text=total_svodka_message
                                                        )
                            except Exception as ex:
                                print(ex)
                            svodka_message_timer = time.time() # обновим таймер сводки
                else:
                    time.sleep(15)
            except Exception as ex:
                tb_str = traceback.format_exc()
                time_error = datetime.datetime.now()
                log_file = 'Error_logger.txt'
                max_log_size = 10 * 1024 * 1024  # 10MB
                target_log_size = 5 * 1024 * 1024  # 5MB
                try:
                    # Проверяем размер файла
                    if os.path.exists(log_file) and os.path.getsize(log_file) > max_log_size:
                        # Если файл больше 10MB, обрезаем его до 10MB, сохраняя последние записи
                        with open(log_file, 'rb+') as file:  # Открываем в бинарном режиме для корректной работы с размером
                            file_size = os.path.getsize(log_file)
                            bytes_to_keep = min(target_log_size, file_size)
                            file.seek(bytes_to_keep, os.SEEK_SET)
                            file.truncate()  # Обрезаем файл с текущей позиции
                            file.seek(0, os.SEEK_SET)  # Переходим в начало файла
                    time_error = datetime.datetime.now()
                    if admin_module:
                        tb_str = traceback.format_exc()
                        log_text = f"ОШИБКА В цикле открытия и контроля потоков {time_error}\n{ex}\n{tb_str}\n"
                        print(f"ОШИБКА В цикле открытия и контроля потоков {time_error}\n{ex}\n{tb_str}\n")
                    else:
                        log_text = f"ОШИБКА В цикле открытия и контроля потоков {time_error}\n{ex}\n"
                        print(ex)
                    with open(log_file, 'a+', encoding='utf-8-sig') as file:
                        file.write(log_text)
                except Exception as e:
                    print(f"Не удалось записать в лог-файл: {e}")
                time.sleep(10)



        print("ИНТЕРФЕЙС ЗАКРЫТ, ПРЕРЫВАЕМ РАБОТУ АЛГОРИТМА!")
        print(f"стоп событие {stop_event.is_set()}")
        for thread in threads:
            thread.join()  # Ждем завершения каждого потока
            print(f"поток {thread} завершил работу")

        # Запуск вебсокета в отдельном потоке
        # symbol = start_data[3]
        # print(symbol)
        # if symbol not in price_dict:
        #     price_dict[symbol] = deque(maxlen=MAX_PRICES)  # список с ограниченным количеством значений
        # try:
        #     websocket_thread = threading.Thread(target=run_websocket_safe, args=(symbol,), daemon=True)
        #     websocket_thread.start()
        # except Exception as ex:
        #     print(f"Ошибка во время запуска сокета {ex}")

        # Запуск торгового алгоритма в основном потоке
        # print("Запуск торгового алгоритма")
        # esm_crypto_bul(start_data)
        #esm_crypto_bul(demo_flag,security_check_flag,exp_check_flag,ticket,admin_module,chat_ids,preset_dict)



    except Exception as ex:
        tb_str = traceback.format_exc()
        time_error = datetime.datetime.now()
        log_file = 'Error_logger.txt'
        max_log_size = 10 * 1024 * 1024  # 10MB
        target_log_size = 5 * 1024 * 1024  # 5MB
        try:
            # Проверяем размер файла
            if os.path.exists(log_file) and os.path.getsize(log_file) > max_log_size:
                # Если файл больше 10MB, обрезаем его до 10MB, сохраняя последние записи
                with open(log_file,'rb+') as file:  # Открываем в бинарном режиме для корректной работы с размером
                    file_size = os.path.getsize(log_file)
                    bytes_to_keep = min(target_log_size, file_size)
                    file.seek(bytes_to_keep, os.SEEK_SET)
                    file.truncate()  # Обрезаем файл с текущей позиции
                    file.seek(0, os.SEEK_SET)  # Переходим в начало файла
            time_error = datetime.datetime.now()
            if admin_module:
                tb_str = traceback.format_exc()
                log_text = f"ОШИБКА В main_user_function {time_error}\n{ex}\n{tb_str}\n"
                print(f"ОШИБКА В main_user_function {time_error}\n{ex}\n{tb_str}\n")
            else:
                log_text = f"ОШИБКА В main_user_function {time_error}\n{ex}\n"
                print(ex)
            with open(log_file, 'a+', encoding='utf-8-sig') as file:
                file.write(log_text)
        except Exception as e:
            print(f"Не удалось записать в лог-файл: {e}")

        time.sleep(15)
    #TODO включить это для работы с сокетами. ИЗ СОКЕТОВ УБРАТЬ СТОП ИВЕНТ
    # except KeyboardInterrupt:
    #     print("Завершение работы...")
    #     stop_event.set()
    # finally:
    #     print("Завершение потоков...")
    #     stop_event.set()
    #     time.sleep(2)  # Даем время потоку завершиться
    #     print("Потоки завершены")
