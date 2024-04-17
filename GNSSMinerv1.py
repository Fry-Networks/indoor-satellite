"""
Satellite Miner ver. 2.2.1
"""

import serial
import datetime
import os
import pysftp
import json
from cryptography.fernet import Fernet
import uuid
import serial.tools.list_ports
from time import sleep
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import requests
import socket
import platform

alreadyTriedPorts = []
title = "frycrypto_api"
MBU = 'http://64.31.28.48'
PPT = 8480
AT = ""


def find_available_serial_port():
    available_ports = list(serial.tools.list_ports.comports())
    print("available_ports:", available_ports)
    for port, desc, hwid in available_ports:
        print("port:", port, "desc :", desc, "hwid :", hwid)
        if "usb" in str(hwid).lower() and (port not in alreadyTriedPorts):
            return port
    return None


def open_serial_connection(port, baudrate=9600, timeout=1):
    try:
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        return ser
    except serial.SerialException:
        return None


# Function to decrypt config file
def owen_decrypt(key, ciphertext):
    nonce, ct = ciphertext[:16], ciphertext[16:]
    cipher = Cipher(algorithms.ChaCha20(key, nonce), mode=None, backend=default_backend())
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ct) + decryptor.finalize()
    return plaintext


def decrypt_config():
    dlt = b'\xd5\xb0\x02\xd8\xf0\xad\xbb6!\xa9\x08gX\x0f\xee\x99\x07rR!\xa0Z\x8b\xd1o\xcd\x9c\nA\x95\xe0\x8a'
    dlp = b'y\x8d\xe7\xe2\x98\x10N|q\xb26\xe0\xe2\x81+\x86\x9f\xb3\x9d\xfdax\xbc}\x17\xe2\xfc\xc9\xc0\x96\x93zI\xfa\x8d\xed\xd4\xdc\x85\xff-\x05\x1f\x97wN\x1e|Z\xa2\xf1\xd9\xc0\x96\xb6\x03\xf7\x1b\xc2\xbf'
    knt = b"0\xf4\x92:C'\xefz\x8c\xc2{l\xbf\xae\xf0_\x06\x1c>b\xdfHMH\x00n\x94\xf6L\xf1\x8c\x07"
    knp = b'Y\xae\xef3V}>\x85\\E\x05\xd8\xf4-M\xd5\xce\x11\xac\xbb\xcd\xcdD5\xe6\xb3\xb4\xb6^\xf6\xba}K\x0bQ\xd5\xee:$J\xad\x87\x8dG\x97\x03&\xac@4#\x8fi/\xbd\x90{\x9a\xefW3\xa8\xe3\xa2I\xef\xad\x15\xc5\xbe\xa4\xff\x04Tt\xac\x98\x02\x8d\x8a\xa2\x96\x8f\xc5\x9c\x14\x10m3s+\xb1@\x9b\xd8\xdf>K\x13\xf6\xd9\r\x99c\xa89s\xc54\x9dW\xa3\x01 \xb2-\x08\x8c\x0f6(\xb6M]\xa0`\xc6\xca\xf0(\x1b\xe6\xd4\xf86b\x94\xf2\xbc\x90\x8c\x1dB\xdd\xee\xf3\x97\x94\xe55\x83\xa5\x05\x90\x89H.\x95;#1\xbf\x9aG\xc4\x07`\xef[(\x83sy\xdb\xedf\xcf\r\xe2\xb8v\xbd\x1b\xafK\xa7Y\xcd\x96d9\xa6C\x95?6jE\x15v\x0f*\x1f\x94<\xd2\xa1\x8a!\xad.\xf6\x18t\x93$\xc7B#\xe7\xa6\xca*.t7\x97M\x99V\xc3J\xfd\xbe\xc2\x1f\x83\xd5oy\x95\xd5\xe8\xed\xfale\xbe\xb6\xb0K\x03\x19\xe0r\x08\x00\x1eF\xe5XM\xb8\xc4^`\xa5\xd9gc\xfa*\xd2Y\xb2\x1dY\xb61\xcf\xd7\xd0\xaf\xb7p0\x15\x86\x16\xf5\xd3\xdfh\xc7+\xdf\x9a\xfa\xd5\xbc\xb6\xf2\xa3\xb5\x01L0\x9e'

    kas = owen_decrypt(dlt, dlp)
    cipher = Fernet(kas)
    ec = owen_decrypt(knt, knp)
    config = json.loads(cipher.decrypt(ec))
    return config


config = decrypt_config()
config_port = config['serial_port']
ports = serial.tools.list_ports.comports()
# ser = serial.Serial(port="COM4", baudrate=9600, timeout=1)
# print("====>", config)
ser = open_serial_connection(config_port)
alreadyTriedPorts.append(config_port)


# ser = None

def checkDeviceConnectionAndAutoConnect():
    global ser
    if ser is None:
        print(f"[!] Could not open port: {config_port}")
        available_port = find_available_serial_port()
        alreadyTriedPorts.append(available_port)

        if available_port:
            print(f"[_] Found available port: {available_port}")
            ser = open_serial_connection(available_port)
        else:
            print("[_] No available serial ports found.")


connectionCheckOK = False
if ser:
    print("[_] port connected.")
    while not connectionCheckOK:
        print("[_] connection check...")
        data = ser.readline().decode('utf-8').strip()
        sleep(1)
        if data:
            print("[_] Received data - validating...")
            samples = ["GPVTG", "GPGGA", "GPGSA", "GPGSV", "GPGLL", "GPTXT", "GPRMC"]
            for sample in samples:
                if sample in data:
                    connectionCheckOK = True
                    break
            if not connectionCheckOK:
                ser = None
                checkDeviceConnectionAndAutoConnect()
        else:
            ser = None
            print("[_] checking other ports...")
            checkDeviceConnectionAndAutoConnect()

# Get MAC address
mac = '-'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 8 * 6, 8)][::-1])
print("[!] MAC Address: ", mac)


def write_to_log(data, current_file):
    now = datetime.datetime.now()
    with open(current_file, 'a') as f:
        f.write(f"{now.strftime('%H:%M:%S')} - {data}\n")

def get_ip_address():
    try:
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to a remote server (doesn't actually send any data)
        s.connect(("8.8.8.8", 80))
        # Get the socket's local address, which is the IP address of the machine
        ip_address = s.getsockname()[0]
        return ip_address
    except Exception as e:
        print("An error occurred while getting IP address:", e)
        return None


def get_device_info():
    try:
        # Get device name
        device_name = platform.node()
        # Get system information
        system_info = platform.system() + ' ' + platform.release()
        # Get hardware information
        hardware_info = platform.machine()

        return f"{device_name}_{system_info}_{hardware_info}"
        # return {
        #     'Device Name': device_name,
        #     'System': system_info,
        #     'Hardware': hardware_info
        # }
    except Exception as e:
        print("An error occurred while getting device information:", e)
        return None
def connection_request():
    global AT
    url = f'{MBU}:{PPT}/client/clientCheck'
    headers = {
        'Content-Type': 'application/json'  # Adjust content type if necessary
    }

    ip_address = get_ip_address()
    if ip_address:
        print("IP Address:", ip_address)
    else:
        print("Failed to get IP address.")
        ip_address = "no visible IP found"

    device_info = get_device_info()
    if device_info:
        print("Device info: ", device_info)
    else:
        print("Failed to get device information.")
        device_info = "could not retrieve"

    body_params = {
        'macAddress': f'{mac}',
        'userDeviceInfo': f'{device_info}',
        'ipAddress': f'{ip_address}'
    }

    try:
        response = requests.post(url, json=body_params, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        # print("Response: ", response.json())
        if response.json():
            resObj = response.json()
            print("[*] Connection check done.")
            status = resObj['status']
            if(status == 'success'):
                print("[*] Connection success.")
                teles = resObj['token']
                if(len(teles) > 0):
                    # print("[*] Token success.: ", teles)
                    AT = teles
                    # upload_file("FRYgnss_f8-59-71-4d-01-8f_01192024_200736.log", "FRYgnss_f8-59-71-4d-01-8f_01192024_200736.log")
        else:
            print("Failed to get response.json() information.")
        return response.json()  # Return response JSON
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


def upload_file(file_name, file_path):
    print("[*] uploading...")
    url = f'{MBU}:{PPT}/uploads/file'

    headers = {
        'Authorization': f'{title} {AT}'
    }

    body_params = {
        'macAddress': f'{mac}',
        'uploadTime': f'{now}',
        'uploadFileName': f'{file_name}',
        'type': 'Satellite_Miner_indoor'
    }

    try:
        with open(file_path, 'rb') as file:
            files = {'uploadFile': (file.name, file, 'multipart/form-data')}
            response = requests.post(url, files=files, data=body_params, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors
            # print("Response: ", response.json())
            print("[*] Upload success.")
            return response.json()  # Return response JSON
    except FileNotFoundError:
        print("File not found.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


now = datetime.datetime.now()
current_file = f"FRYgnss_{mac}_{now.strftime('%m%d%Y_%H%M%S')}.log"

last_upload_hour = now.hour


connection_request()

if connectionCheckOK:
    while True:
        data = ser.readline().decode('utf-8').strip()
        if data:  # if data is not empty
            print(f"[_] Received: {data}")
            write_to_log(data, current_file)
            now = datetime.datetime.now()
            if now.hour != last_upload_hour:
                # upload_to_sftp(current_file)
                upload_file(current_file, current_file)
                last_upload_hour = now.hour
                current_file = f"FRYgnss_{mac}_{now.strftime('%m%d%Y_%H%M%S')}.log"
else:
    print("[!] Could not find any available ports. Please check your GPS device and try again.")
