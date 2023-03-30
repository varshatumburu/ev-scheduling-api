
from flask import Flask, request
import json
import pandas as pd
import datetime
import modules.matching as matching, modules.helper as helper
import math
from modules.scheduler import SLOT_TIME
import config

app = Flask(__name__)

@app.post("/")
def schedule_request():
    if request.is_json:
        request_data = request.get_json()

    start_time = request_data['start_time']
    end_time = request_data['end_time']
    cs_queue = request_data['cs_queue']
    soc = request_data['soc']
    vehicle_type = request_data['vehicle_type']
    bcap = request_data['battery_capacity']
    mileage = request_data['mileage']

    # retrieve already scheduled info/ datasets
    existing_requests = pd.read_json('datasets/requests.json')
    charging_stations = pd.read_json('datasets/charging_stations.json')
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
    new_idx = max(existing_requests['index'])+1
    new_request = pd.DataFrame(data={
            "index": new_idx,
			"start_time": start_time,
			"end_time": end_time,
            "Available from": str(datetime.time(int(start_time)//60, int(start_time)%60)),
            "Available till": str(datetime.time(int(end_time)//60, int(end_time)%60)),
            "current_soc": soc,
            "battery_capacity": bcap,
            "mileage": mileage,
            "vehicle_type": vehicle_type
        }, index=[0])
    updated_requests = pd.concat([new_request, existing_requests[:]]).drop_duplicates().reset_index(drop=True)
    config.REQUESTS = updated_requests

    config.SLOT_MAPPING = existing_schedule
    config.POSSIBLE_SLOTS = existing_pslots
    flag=0
    while len(cs_queue)!=0:
        port_id = cs_queue.pop(0)
        
        csno, portno = int(port_id.split('p')[0]), int(port_id.split('p')[1])
        charging_port = charging_stations.to_dict("records")[csno]["ports"][portno]

        stime = helper.roundup(start_time)
        duration = helper.find_duration(charging_port['power'], bcap)
        nslots = int(math.ceil(duration/SLOT_TIME))
        config.REQUIRED_SLOTS[new_idx] = nslots
        matched_slots = []
        while stime+duration<=end_time:
            matched_slots.append(int(stime/SLOT_TIME))
            stime += SLOT_TIME

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
            print(f"\n>>> REQUEST ACCEPTED! Accommodated in Port {port_id}")
            flag=1
            json_object = json.dumps(config.SLOT_MAPPING, indent=4)
            with open("datasets/slot_mapping.json","w") as f: f.write(json_object)

            updated_requests.to_json('datasets/requests.json', orient="records", indent=4)
            return json.dumps({"id": new_idx, "success":flag, "port": port_id, "message":"request accepted"})
        else:
            config.REQUEST_MAPPING[port_id].remove(new_idx)
            # delete slots that aren't possible anymore
            del config.POSSIBLE_SLOTS[port_id][new_idx]

    if(flag==0): 
        print("\n>>> REQUEST DENIED.")

        updated_requests.to_json('datasets/requests.json', orient="records", indent=4)
        return json.dumps({"id": new_idx,"success":flag, "message":"request denied"})

if __name__ == '__main__':
    app.run(debug = True)
