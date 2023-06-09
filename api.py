
from flask import Flask, request
import json
import modules.matching as matching, modules.helper as helper
import math
from modules.scheduler import SLOT_TIME
import config
from queue import PriorityQueue
import time
from datetime import datetime
import threading
import gspread

app = Flask(__name__)
connection = 0
try:
    client = gspread.service_account(filename="ev-scheduling-api-790eaa603b7f.json")
    sheet = client.open("EV-Schedule")
    connection = 1
except:
    print("Cannot connect to gsheets")

charging_stations = json.load(open('datasets/ev_stations.json'))
config.CHARGING_STATIONS = charging_stations
timers = {}

def update_gsheet(station):
    if(connection):
        updated_schedule = {k:v for k,v in config.SLOT_MAPPING.items() if k.startswith(station)}
        try:
            worksheet = sheet.worksheet(station)
            worksheet.clear()
        except:
            worksheet=sheet.add_worksheet(title=station, rows="100", cols="10")

        header_row = ['TimeStamp', 'Port ID', 'Time Slot', 'Request ID']
        worksheet.append_row(header_row)

        for port, schedule in updated_schedule.items():
            cs, pt = port.split('__')

            for time_slot, req_id in schedule.items():
                ts = [req['time_stamp'] for req in config.REQUESTS if req['index']==req_id][0]
                worksheet.append_row([ts, pt, time_slot, req_id])

        print('Data updated!')
    else:
        print("Connection to gsheets failed.")

@app.post("/check")
def schedule_request():
    try:
        request_data = request.get_json()

        start_time = request_data['start_time']
        end_time = request_data['end_time']
        cs_queue = request_data['cs_queue']
        bcap = request_data['battery_capacity']
        connectorTypes = request_data['connectors']
    
    except: 
        return json.dumps({"Error":"Input Data Error", "Message":"Input data not given or not in JSON format"})

    # retrieve already scheduled info/ dataset
    existing_requests = json.load(open('datasets/requests.json'))
    raw_schedule = json.load(open('datasets/slot_mapping.json'))
    raw_pslots = json.load(open('datasets/possible_slots.json'))

    # Type cast keys to int 
    existing_schedule = {}
    for port, val in raw_schedule.items():
        existing_schedule[port] = {int(k):v for k,v in val.items()}
        
    # Type cast keys to int 
    existing_pslots = {}
    for port, val in raw_pslots.items():
        existing_pslots[port] = {int(k):v for k,v in val.items()}

    # try to fit new request
    try:
        new_idx = max([d['index'] for d in existing_requests])+1
    except:
        new_idx=0

    dt = datetime.now()
    ts = time.mktime(dt.timetuple())
    sp = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    print(sp)
    new_request = {
            "index": new_idx,
            "time_stamp": sp,
			"start_time": start_time,
			"end_time": end_time,
            "battery_capacity": bcap,
            "connectors": connectorTypes
        }
    existing_requests.append(new_request)
    config.REQUESTS = existing_requests

    timers[new_idx]=time.time()

    config.SLOT_MAPPING = existing_schedule
    config.POSSIBLE_SLOTS = existing_pslots
    flag=0
    if len(cs_queue)==0:
        return json.dumps({"Error":"Scheduling Error", "Message":"No ports given in priority to schedule charging"})
    
    ports_priority = []
    stime = {}; etime={}
    for idx, cs_key in enumerate(cs_queue):
        stime[cs_key] = start_time[idx]
        etime[cs_key]=end_time[idx]

        ports = charging_stations[cs_key]['chargingPark']['connectors']
        q = PriorityQueue()
        for port in ports:
            # if port and vehicle specifications match
            if port['connectorType'] in connectorTypes:
                duration = helper.find_duration(port['ratedPowerKW'], bcap)
                q.put((duration, port['id']))

        while not q.empty():
            (dur, portid) = q.get()
            ports_priority.append((cs_key+'__'+str(portid), dur))

    while len(ports_priority)!=0:
        (port_id, duration) = ports_priority.pop(0)
        cs_key, portno = port_id.split('__')[0], int(port_id.split('__')[1])

        begin = helper.roundup(stime[cs_key]); end = etime[cs_key]
        nslots = int(math.ceil(duration/SLOT_TIME))
        config.REQUIRED_SLOTS[new_idx] = nslots
        matched_slots = []
        while begin+duration<=end:
            matched_slots.append(int(begin/SLOT_TIME))
            begin += SLOT_TIME

        if(config.POSSIBLE_SLOTS.get(port_id)==None):
            config.POSSIBLE_SLOTS[port_id]={}
        config.POSSIBLE_SLOTS[port_id][new_idx]=matched_slots

        graphs_object = json.dumps(config.POSSIBLE_SLOTS, indent=4)
        with open("datasets/possible_slots.json","w") as f: f.write(graphs_object)
        
        if(config.REQUEST_MAPPING.get(port_id)==None):
            config.REQUEST_MAPPING[port_id]=[]
        config.REQUEST_MAPPING[port_id].append(new_idx)

        if(config.SLOT_MAPPING.get(port_id)==None): 
            config.SLOT_MAPPING[port_id]={}

        if(matching.kuhn(new_idx, config.VISITED, 0, config.SLOT_MAPPING, port_id)):
            print(f"\n>>> REQUEST ACCEPTED! Can be accommodated in Port {port_id}")
            flag=1
            update_gsheet(port_id.split('__')[0])

            json_object = json.dumps(config.SLOT_MAPPING, indent=4)
            with open("datasets/slot_mapping.json","w") as f: f.write(json_object)

            updated_requests = json.dumps(config.REQUESTS, indent=4)
            with open("datasets/requests.json","w") as f: f.write(updated_requests)
            return json.dumps({"id": new_idx, "success":flag, "station_id": cs_key, "port": portno, "chargingTime": duration, "message":"request accepted"})
        else:
            config.REQUEST_MAPPING[port_id].remove(new_idx)
            # delete slots that aren't possible anymore
            del config.POSSIBLE_SLOTS[port_id][new_idx]

    if(flag==0): 
        print("\n>>> REQUEST DENIED.")

        updated_requests = json.dumps(config.REQUESTS, indent=4)
        with open("datasets/requests.json","w") as f: f.write(updated_requests)

        return json.dumps({"id": new_idx,"success":flag, "message":"request denied"})
    
@app.post("/confirm")
def confirm_request():
    try:
        request_data = request.get_json()
        requests = request_data['request_id']

    except:
        return json.dumps({"Success":0,"Error":"Input Data Error", "Message":"Input data not given or not in JSON format"})
    
    for req_idx in requests:
        try:
            del timers[req_idx]
        except:
            return json.dumps({"Success":0,"Error":"Index Error", "Message": "Request not registered."})

    return json.dumps({"Success":1, "Message":"Slots confirmed. Success!"})

def check_expired_requests():
    print("Checking expired requests! 1min done")
    fl=0; removed = []; stations = []
    for request_id, start_time in timers.items():
        # print(request_id, start_time)
        current_time = time.time()
        if current_time - start_time >= config.EXPIRY_THRESHOLD:
            port_id, slot, nslots = config.SCHEDULE_FIT[request_id]
            # print(port_id, slot, nslots)
            for i in range(nslots):
                fl=1
                removed.append(request_id)
                stations.append(port_id.split('__')[0])
                del config.SLOT_MAPPING[port_id][slot+i]

    for req in removed:
        if timers.get(req)!=None:
            del timers[req]

    if fl:
        print("Removing expired slots...")
        for st in stations:
            update_gsheet(st)

        json_object = json.dumps(config.SLOT_MAPPING, indent=4)
        with open("datasets/slot_mapping.json","w") as f: f.write(json_object)

    threading.Timer(60.0,check_expired_requests).start()

check_expired_requests()

if __name__ == '__main__':
    app.run(debug = True)
