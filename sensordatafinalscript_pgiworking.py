import pymysql
from datetime import datetime
import serial
import re

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'pgichandigarh',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

db_connection = pymysql.connect(**db_config)
cursor = db_connection.cursor()

ser = serial.Serial('COM3', baudrate=9600, timeout=1)
#ser = 1

VALID_SENSOR_COUNTS = {
    2: {1: 11, 2: 18, 3: 19, 4: 42},
    3: {1: 18, 2: 16, 3: 40, 4: 12}
}

def update_sensor_data(floor_id, zone_id, sensor_id, status):
    try:
        query = """
            INSERT INTO sensor (floor_id, zone_id, sensor_id, status, count, last_updated)
            VALUES (%s, %s, %s, %s, 1, %s)
            ON DUPLICATE KEY UPDATE status = %s, count = count + 1, last_updated = %s
        """
        now = datetime.now()
        cursor.execute(query, (floor_id, zone_id, sensor_id, status, now, status, now))
        db_connection.commit()
    except pymysql.Error as err:
        print(f"Error: {err}")

def insert_activity_log(floor_id, zone_id, sensor_id, issue):
    try:
        query = """
            INSERT INTO activity_logs (floor_id, zone_id, sensor_id, issue, created_at)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE issue = VALUES(issue), created_at = VALUES(created_at)
        """
        cursor.execute(query, (floor_id, zone_id, sensor_id, issue, datetime.now()))
        db_connection.commit()
    except pymysql.Error as err:
        print(f"Error: {err}")

def insert_line_chart_data(floor_id, zone_id, total_available, total_vacant, total_faulty):
    try:
        query = """
            INSERT INTO line_chart (floor_id, zone_id, total_available, total_vacant, total_faulty)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (floor_id, zone_id, total_available, total_vacant, total_faulty))
        db_connection.commit()
    except pymysql.Error as err:
        print(f"Error: {err}")

def extract_sensor_data(byte_data, zone_start_index, floor_id, zone_id):
    end_index = byte_data.find(b'\x55', zone_start_index)
    if end_index == -1 or end_index - zone_start_index < 8:
        return None

    zone_address = byte_data[zone_start_index + 1]
    zone_status = byte_data[zone_start_index + 2]
    if zone_status == 3:
        return None

    total_sensors = byte_data[zone_start_index + 3]
    expected_length = 4 + total_sensors
    actual_length = end_index - zone_start_index

    if actual_length <= expected_length:
        return None

    sensor_data = [byte_data[zone_start_index + 4 + i] for i in range(total_sensors)]

    return {
        'floor_id': floor_id,
        'zone_id': zone_id,
        'zone_address': zone_address,
        'zone_status': zone_status,
        'total_sensors': total_sensors,
        'sensor_data': sensor_data,
        'total_vacant': sensor_data.count(0),
        'total_engaged': sensor_data.count(1),
        'total_faulty_sensors': sensor_data.count(2) + sensor_data.count(3),
        'total_nocom_sensors': sensor_data.count(3)
    }

previous_status = {}

while True:
    floor_data = ser.readline()
    #floor_data = b'\xf4\x01\x02\x01\x00\x04\xaa\x01\x01\x0b\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0b\x00\x00\x00U\xaa\x01\x03U\xaa\x03\x01\x13\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12\x00\x00\x01U\xaa\x04\x01*\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00*\x00\x00\x00U\x00Z\x00Y\x00\x00\x00\x01\x00\xe9\x00\xb0\x00\xa4\x00\x01\x00\x0b\x00\xd1'
    print("Data read:", floor_data)

    if not (floor_data.startswith(b'\xF4') and floor_data.endswith(b'\xD1')):
        continue

    floor_id = floor_data[3]
    print(f"Detected Floor ID: {floor_id}")

    matches = re.findall(b'\xF4.*?\xD1', floor_data, re.DOTALL)

    for match in matches:
        byte_data = match
        zone_start_index = byte_data.find(b'\xAA')

        # Use sensor count to determine floor_id
        total_sensors = byte_data[zone_start_index + 3] if zone_start_index != -1 else None
        floor_id = 2 if (zone_start_index != -1 and total_sensors == 11) else 3

        zone_data_list = []
        is_valid_floor_data = True

        while zone_start_index != -1:
            zone_id = byte_data[zone_start_index + 1]
            zone_data = extract_sensor_data(byte_data, zone_start_index, floor_id, zone_id)

            if zone_data:
                expected_count = VALID_SENSOR_COUNTS.get(floor_id, {}).get(zone_id)
                if expected_count != len(zone_data['sensor_data']):
                    print(f"[SKIPPED] Floor {floor_id}, Zone {zone_id}: Expected {expected_count}, got {len(zone_data['sensor_data'])}")
                    is_valid_floor_data = False
                    break
                zone_data_list.append(zone_data)
            else:
                print(f"[ERROR] Invalid data for Floor {floor_id}, Zone {zone_id}")
                is_valid_floor_data = False
                break

            zone_start_index = byte_data.find(b'\xAA', zone_start_index + 1)

        if is_valid_floor_data:
            print(f"[VALID DATA] Inserting all zone data for Floor {floor_id}...")
            for zone_data in zone_data_list:
                insert_line_chart_data(
                    zone_data['floor_id'],
                    zone_data['zone_id'],
                    len(zone_data['sensor_data']),
                    zone_data['total_vacant'],
                    zone_data['total_faulty_sensors']
                )

                for sensor_id, status in enumerate(zone_data['sensor_data'], start=1):
                    key = (zone_data['floor_id'], zone_data['zone_id'], sensor_id)
                    if previous_status.get(key) != status:
                        update_sensor_data(*key, status)
                        previous_status[key] = status
                    if status == 3:
                        insert_activity_log(*key, "Faulty")
        else:
            print(f"[SKIPPED FLOOR] Floor {floor_id}: Incomplete or invalid zone data")

cursor.close()
db_connection.close()
