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
MBU = 'https://datastorage.frynetworks.com'
PPT = 8480
AT = ""
minerKey = ""

def getMinerKey():
    global minerKey

    try:
        with open("minerkey.txt", 'r') as minerKeyFile:
            minerKey = minerKeyFile.readline()
        return minerKey
    except FileNotFoundError:
        print("Miner Key File 'minerkey.txt' not found.")
        return None
    except Exception as e:
        print("An error occurred:", e)
        return None

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

getMinerKey()
config_port = 'COM3'
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

def read_file_without_newlines(file_path):
    try:
        with open(file_path, 'r') as file:
            lines = [line.strip() for line in file.readlines()]
        return lines
    except FileNotFoundError:
        print("File not found.")
        return None
    except Exception as e:
        print("An error occurred:", e)
        return None

def connection_request():
    global AT
    url = f'{MBU}/api/data/save'
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
                    # upload_file("FRYgnss_f8-59-71-4d-01-92_04172024_032102.log", "FRYgnss_f8-59-71-4d-01-92_04172024_032102.log")
        else:
            print("Failed to get response.json() information.")
        return response.json()  # Return response JSON
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


def upload_file(file_name, file_path):
    global minerKey
    print("[*] uploading...")
    url = f'{MBU}/api/data/save'

    # headers = {
    #     'Authorization': f'{title} {AT}'
    # }

    headers = {
        'Content-Type': 'application/json'  # Adjust content type if necessary
    }



    try:
        with open(file_path, 'rb') as file:
            lines_without_newlines = read_file_without_newlines(file_path)
            if lines_without_newlines:
                print(lines_without_newlines)
                data_params = {
                    'macAddress': f'{mac}',
                    'uploadTime': f'{now}',
                    'uploadFileName': f'{file_name}',
                    'type': 'Satellite_Miner_indoor',
                    'uploadFileData': lines_without_newlines
                }
                body_params = {
                    'minerkey': f'{minerKey}',
                    'data': data_params
                }
                response = requests.post(url, data=body_params, headers=headers)
                response.raise_for_status()  # Raise an exception for HTTP errors
                print("Response: ", response.json())
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

# last_upload_hour = now.hour
last_upload_time = now


# connection_request()
# upload_file("FRYgnss_f8-59-71-4d-01-92_04172024_032102.log", "FRYgnss_f8-59-71-4d-01-92_04172024_032102.log")

if connectionCheckOK:
    while True:
        data = ser.readline().decode('utf-8').strip()
        if data:  # if data is not empty
            print(f"[_] Received: {data}")
            write_to_log(data, current_file)
            now = datetime.datetime.now()
            compare5mins = now - datetime.timedelta(minutes=5)
            print("===> Now mins: ", now, " compare5mins : ", compare5mins)
            if last_upload_time <= compare5mins:
                # upload_to_sftp(current_file)
                upload_file(current_file, current_file)
                last_upload_time = now
                current_file = f"FRYgnss_{mac}_{now.strftime('%m%d%Y_%H%M%S')}.log"
else:
    print("[!] Could not find any available ports. Please check your GPS device and try again.")
