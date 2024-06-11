# pgs_django_backened_supremecourt
supremecourt pgs django_project 
ye humara supre court ka backened hai. isme humne sensor ke data ko database me store karwaya tha script ke jariye python me. aur waha se django me rest api ka use karke hum data send kiye hai react js ke fronted me


Note- is code me maine ek dictionary banaya hai kyuki kabhi kabhi kya hota hai ki jab mai sensors count krta hu total sensors ka to sensor se jo data hai wo to mil jata hai mujhe lekin mai ye kaise match karunga ki actual scenario me bhi usme itne hi sensors lage hai. to mai simply dictionary bana liya hu floor1 aur floor2 ke liye aur floor 1 ke each zone me kitne sensors lage hai usko bhi likh diya hu isme. jisse humara problem resolve ho gya hai

expected_sensors = {
    1: {1: 27, 2: 23, 3: 27, 4:40 , 5:22},  # Example for floor 1
    2: {1: 34, 2: 19, 3: 27, 4:39 , 5:23 }   # Example for floor 2
}

while True:
    floor_data = ser.readline()
    # Accumulate data until a complete "F4 to D1" packet is received
    while not (floor_data.startswith(b'\xF4') and floor_data.endswith(b'\xD1')):
        floor_data += ser.readline()

    print("data read")
    print(floor_data)
    matches = re.findall(b'\xF4.*?\xD1', floor_data, re.DOTALL)
    for match in matches:
        byte_data = match

        zone_start_index = byte_data.find(b'\xAA')
        total_sensors = byte_data[zone_start_index + 3]
        
        if zone_start_index != -1 and total_sensors == 27:
            floor_id = 1
        else:
            floor_id = 2

        while zone_start_index != -1:
            zone_id = byte_data[zone_start_index + 1] + 1
            zone_data = extract_sensor_data(zone_start_index, floor_id, zone_id)
            
            if zone_data is not None:
                print(f"Floor {floor_id}, Zone {zone_id} Data:", zone_data)
                total_available_zone = len(zone_data['sensor_data'])
                total_vacant_zone = zone_data['total_vacant']
                total_faulty_zone = zone_data['total_faulty_sensors']
                total_sensor_zone = zone_data['total_sensors']
                
                if (floor_id in expected_sensors and zone_id in expected_sensors[floor_id] and total_sensor_zone == expected_sensors[floor_id][zone_id]):
                    insert_line_chart_data(floor_id, zone_id, total_available_zone, total_vacant_zone, total_faulty_zone)

                    for sensor_id, status in enumerate(zone_data['sensor_data'], start=1):
                        print(f"Sensor ID: {sensor_id}, Status: {status}")

                        sensor_entry = (zone_data['floor_id'], zone_data['zone_id'], sensor_id, status, datetime.now(), zone_data['total_engaged'])
                        all_sensor_data.append(sensor_entry)

                        if previous_status.get((floor_id, zone_id, sensor_id)) != status:
                            update_sensor_data(floor_id, zone_id, sensor_id, status)

                            previous_status[(floor_id, zone_id, sensor_id)] = status

                        if (status == 3):
                            insert_activity_log(floor_id, zone_id, sensor_id, "Faulty")

            zone_start_index = byte_data.find(b'\xAA', zone_start_index + 1)

ser.close()
cursor.close()
db_connection.close()

Note- if (floor_id in expected_sensors and zone_id in expected_sensors[floor_id] and total_sensor_zone == expected_sensors[floor_id][zone_id]): is line ka ye matlab hai ki floor_id jo hai expected_sensor me hai ki nahi. aur zone_id jo hai wo expected sensor['floor_id'] means floor_id man lo ki 1 hai to expected sensor[1] me means floor_1 wale me jayega aur ab total_sensor_zone == expected_sensors[floor_id][zone_id]) means man lo floor_id 1 hai aur zone_id=1 hai means floor_1 ke andar jayega aur 1st wale ke liye dekhega ki usme kya likha hai. expected[0][0]
