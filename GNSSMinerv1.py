import serial
import datetime
import os
import pysftp
import json
from cryptography.fernet import Fernet
import uuid

# Function to decrypt config file
def decrypt_config():
    with open("key.key", "rb") as key_file:
        key = key_file.read()
    cipher = Fernet(key)
    with open("config.json.enc", "rb") as file:
        encrypted_config = file.read()
    config = json.loads(cipher.decrypt(encrypted_config))
    return config

config = decrypt_config()

ser = serial.Serial(port=config['serial_port'], baudrate=9600, timeout=1)

# Get MAC address
mac = '-'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0,8*6,8)][::-1])

def write_to_log(data, current_file):
    now = datetime.datetime.now()
    with open(current_file, 'a') as f:
        f.write(f"{now.strftime('%H:%M:%S')} - {data}\n")

def upload_to_sftp(current_file):
    remote_filename = f"/home/fryscrypto/indoor_gnss/{current_file}"
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None  # Disable host key checking.
    with pysftp.Connection(config['host'], username=config['username'], password=config['password'], cnopts=cnopts) as sftp:
        sftp.put(current_file, remote_filename) 
    os.remove(current_file)

now = datetime.datetime.now()
current_file = f"FRYgnss_{mac}_{now.strftime('%m%d%Y_%H%M%S')}.log"

last_upload_hour = now.hour
while True:
    data = ser.readline().decode('utf-8').strip()
    if data:  # if data is not empty
        print(f"Received: {data}")
        write_to_log(data, current_file)
        now = datetime.datetime.now()
        if now.hour != last_upload_hour:
            upload_to_sftp(current_file)
            last_upload_hour = now.hour
            current_file = f"FRYgnss_{mac}_{now.strftime('%m%d%Y_%H%M%S')}.log"
