# -*- coding: utf-8 -*-
"""
MicroDuck 舵机简单控制程序（上位机 + USB转TTL）
用法:
    python servo_test.py            # 自动检测串口
    python servo_test.py COM7       # 指定串口

交互命令:
    2048        -> 舵机转到位置 2048（默认速度）
    2048 300    -> 转到位置 2048，速度 300
    r           -> 读取舵机当前位置
    q           -> 退出
"""
import sys
import os

# 引入飞特 SDK（舵机资料/WTServo_Python-main/FTServo_Python-main）
SDK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '..', '..', '..', '舵机资料', 'WTServo_Python-main', 'FTServo_Python-main')
sys.path.append(SDK_PATH)

import serial.tools.list_ports
from scservo_sdk import *

BAUDRATE = 1000000   # ST3215 默认波特率
SERVO_ID = 1         # 舵机 ID
DEFAULT_SPEED = 1000
DEFAULT_ACC = 50


def find_port():
    """自动查找 USB 转 TTL 串口（CH340/CH343/CP210x/FT232）"""
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        desc = (p.description or '').lower()
        if any(k in desc for k in ['ch340', 'ch343', 'ch341', 'cp210', 'ft232', 'usb-serial']):
            return p.device
    return None


def main():
    port_name = sys.argv[1] if len(sys.argv) > 1 else find_port()
    if not port_name:
        print('未找到 USB 转 TTL 串口，请用命令行参数指定，例如: python servo_test.py COM7')
        return
    print('使用串口: %s  波特率: %d' % (port_name, BAUDRATE))

    portHandler = PortHandler(port_name)
    packetHandler = sms_sts(portHandler)

    if not portHandler.openPort():
        print('打开串口失败，请检查是否被占用')
        return
    if not portHandler.setBaudRate(BAUDRATE):
        print('设置波特率失败')
        return

    # Ping 舵机确认通信正常
    model, result, error = packetHandler.ping(SERVO_ID)
    if result != COMM_SUCCESS:
        print('Ping 失败: %s' % packetHandler.getTxRxResult(result))
        print('请检查: 舵机是否上电 / 接线是否正确(TX、RX并接DATA) / 舵机ID是否为 %d' % SERVO_ID)
        portHandler.closePort()
        return
    print('连接成功! 舵机型号: %d  %s' % (model, packetHandler.getRxPacketError(error) if error else ''))

    # 使能扭力
    packetHandler.write1ByteTxRx(SERVO_ID, SMS_STS_TORQUE_ENABLE, 1)

    print('\n输入位置(0~4095)控制舵机，可带速度如 "2048 300"；输入 r 读位置；q 退出')
    while True:
        try:
            cmd = input('> ').strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not cmd:
            continue
        if cmd.lower() == 'q':
            break
        if cmd.lower() == 'r':
            pos, result, error = packetHandler.ReadPos(SERVO_ID)
            if result == COMM_SUCCESS:
                print('当前位置: %d %s' % (pos, packetHandler.getRxPacketError(error) if error else ''))
            else:
                print('读取失败: %s' % packetHandler.getTxRxResult(result))
            continue
        parts = cmd.split()
        try:
            position = int(parts[0])
            speed = int(parts[1]) if len(parts) > 1 else DEFAULT_SPEED
            if not 0 <= position <= 4095:
                print('位置超出范围 0~4095')
                continue
        except ValueError:
            print('无效输入，示例: 2048 或 2048 300')
            continue
        result, error = packetHandler.WritePosEx(SERVO_ID, position, speed, DEFAULT_ACC)
        if result != COMM_SUCCESS:
            print('指令失败: %s' % packetHandler.getTxRxResult(result))
        elif error != 0:
            print('舵机报警: %s' % packetHandler.getRxPacketError(error))
        else:
            print('已发送: 位置=%d 速度=%d' % (position, speed))

    # 退出前关闭扭力
    packetHandler.write1ByteTxRx(SERVO_ID, SMS_STS_TORQUE_ENABLE, 0)
    portHandler.closePort()
    print('已退出')


if __name__ == '__main__':
    main()
