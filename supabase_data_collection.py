from machine import Pin, I2C
import time
import math
import struct
import network
import urequests
import ujson

# ========= I2C 初始化 =========
i2c = I2C(
    0,
    scl=Pin(4),
    sda=Pin(5),
    freq=400_000
)

MPU_ADDR = 0x68

# ========= 基本寄存器 =========
WHO_AM_I     = 0x75
PWR_MGMT_1   = 0x6B
ACCEL_CONFIG = 0x1C
ACCEL_XOUT_H = 0x3B

# ========= WiFi 连接 =========
SSID = "XXXX"
PASSWORD = "xxxxxxxxx"

SUPABASE_URL = "https://tvselobkki.supabase.co"
SUPABASE_KEY = "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2c2Vsb2Jra2lpbndhaGNwa2N5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI1NjE2MTYsImV4cCI6MjA4ODEzNzYxNn0.MZR4fPzQ4K_FimwME4wyBXdWl92OCeTmLVuiVMaGkpI"

TABLE = "sensor_data"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)

    # 先关闭再打开
    wlan.active(False)
    time.sleep(1)
    wlan.active(True)
    time.sleep(1)

    if not wlan.isconnected():
        print("Connecting WiFi...")
        wlan.connect(SSID, PASSWORD)

        timeout = 10
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print("...")

    if wlan.isconnected():
        print("WiFi connected:", wlan.ifconfig())
    else:
        print("WiFi failed")
    
# ========= 传感器初始化 =========
def mpu_init():
    # 唤醒
    i2c.writeto_mem(MPU_ADDR, PWR_MGMT_1, b'\x00')
    time.sleep_ms(100)

    # 加速度量程 ±4g（对姿态很友好）
    i2c.writeto_mem(MPU_ADDR, ACCEL_CONFIG, b'\x08')
    time.sleep_ms(10)

    who = i2c.readfrom_mem(MPU_ADDR, WHO_AM_I, 1)[0]
    print("WHO_AM_I:", hex(who))

# ========= 读取加速度 =========
def read_accel_raw():
    data = i2c.readfrom_mem(MPU_ADDR, ACCEL_XOUT_H, 6)
    ax, ay, az = struct.unpack(">hhh", data)
    return ax, ay, az

# ========= 计算 Pitch / Roll =========
def calc_pitch_roll(ax, ay, az):
    # 转 float
    ax = float(ax)
    ay = float(ay)
    az = float(az)

    roll = math.atan2(ay, az)
    pitch = math.atan2(-ax, math.sqrt(ay * ay + az * az))

    # 弧度 → 角度
    roll_deg = roll * 180.0 / math.pi
    pitch_deg = pitch * 180.0 / math.pi

    return pitch_deg, roll_deg
    
# ========= 发送到 Supabase =========
def send_to_supabase(pitch, roll):
    url = SUPABASE_URL + "/rest/v1/" + TABLE

    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_KEY,
        "Authorization": "Bearer " + SUPABASE_KEY
    }

    data = {
        "pitch": pitch,
        "roll": roll
    }

    try:
        response = urequests.post(url, headers=headers, data=ujson.dumps(data))
        print("Sent:", response.text)
        response.close()
    except Exception as e:
        print("Send failed:", e)
        
# ========= 主程序 =========
connect_wifi()
mpu_init()

while True:
    ax, ay, az = read_accel_raw()
    pitch, roll = calc_pitch_roll(ax, ay, az)

    print(
        "AX:{:6d} AY:{:6d} AZ:{:6d} | "
        "Pitch:{:6.2f}° Roll:{:6.2f}°".format(
            ax, ay, az, pitch, roll
        )
    )
    send_to_supabase(pitch, roll)

    time.sleep(2)   # 2秒感觉有点慢，后面再改
