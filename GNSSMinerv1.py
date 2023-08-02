import serial
import datetime
import os
import pysftp
import json
from cryptography.fernet import Fernet
import uuid

# Function to decrypt config file
def decrypt_config():
    key = "REDACTED_ROTATE_ME"
    cipher = Fernet(key)
    # encrypted_config = "gAAAAABkqfR_6bpgHl2DRWjxfaQVfKW0tw8YTauZLYZJU66xLOy7Xsy-OYF0TYvg3uA644GusZd3X__q1cMdoYGnsIaOvl62Bh-VvOKEgp7gmEOdrx0wxPzzvuDPOxC9nyVNDXm-wbf1U7lYQRd7_nfYiDIiQ7nP4aEesxoIqiCW46QCkRuiU3NxBPUxWGAWzlIlVdxVtUWkCjZK5mFzPLntRmXzI7hy7eq07VYCHVWwWhp69Ujb7kA="
    encrypted_config = "gAAAAABkwn6IA2T8YiOAdpFa-WX_1V1mOc3egaT2VoXTeCc8YClBHgLAG0QZQs0W2VEmt-QxHNNB0jDhkqyHPebhXZxvhVTvjEnuOqR2Q7ALhX5e3ox7wgYDzJhGLPjGSgFf6u34MmtKLER-gBIn0U3AeBNe2hQRZLAcHGa9psISSHkvcZpCmo2EV1GXcPgGhLUz0EuKpNUlYPHIhfXvWW0i2NpB5braUNHyWeSMCyEFGqUhUiA4UaaGwjvyiv5EADTyIPU1p7OtxL181A57Xxj_nwTJl-Q0ag=="
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
