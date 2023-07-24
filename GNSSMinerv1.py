import datetime
import os
import pysftp
import uuid
from gps import *
from time import *

gnss = gps(mode=WATCH_ENABLE)

mac = '-'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0,8*6,8)][::-1])

# FTP details
config = {
    "host": "207.244.74.204",
    "username": "fryscrypto",
    "password": "Wtf.7001",
}

last_upload_hour = datetime.datetime.now().hour

# Initialize the current_file variable
now = datetime.datetime.now()
current_file = f"FRYgnss_{mac}_{now.strftime('%m%d%Y_%H%M%S')}.txt"

def write_to_log(gnss_data, current_file):
    now = datetime.datetime.now()
    with open(current_file, 'a') as f:
        f.write(f"{now.strftime('%H:%M:%S')} - {gnss_data}\n")

def upload_to_sftp(current_file, config):
    now = datetime.datetime.now()
    local_filename = current_file
    remote_filename = f"/home/fryscrypto/indoor_gnss/FRYgnss_{mac}_{now.strftime('%m%d%Y_%H%M%S')}.txt"
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None 
    with pysftp.Connection(config['host'], username=config['username'], password=config['password'], cnopts=cnopts) as sftp:
        sftp.put(local_filename, remote_filename)
    os.remove(local_filename)

while True:
    now = datetime.datetime.now()

    # Every 10 seconds write GNSS data to file
    if now.second % 10 == 0:
        gnss_data = gnss.next()  # get gnss data
        write_to_log(gnss_data, current_file)
        print(f"Recorded GNSS data at {now.strftime('%H:%M:%S')}")  # printing for visibility
    
    # Upload the file one minute before the top of the hour
    if now.minute == 59 and now.second == 0:
        upload_to_sftp(current_file, config)

    # Update the filename at the top of the hour
    if now.minute == 0 and now.second == 0 and now.hour != last_upload_hour:
        current_file = f"FRYgnss_{mac}_{now.strftime('%m%d%Y_%H%M%S')}.txt"
        last_upload_hour = now.hour
