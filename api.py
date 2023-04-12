
from flask import Flask, request
import json
import modules.matching as matching, modules.helper as helper
import math
from modules.scheduler import SLOT_TIME
import config
from queue import PriorityQueue

app = Flask(__name__)

charging_stations = json.load(open('datasets/ev_stations.json'))
config.CHARGING_STATIONS = charging_stations

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

    # retrieve already scheduled info/ datasets
    existing_requests = json.load(open('datasets/requests.json'))
    cache = json.load(open('datasets/cache_slots.json'))
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

    new_request = {
            "index": new_idx,
			"start_time": start_time,
			"end_time": end_time,
            # "Available from": str(datetime.time(int(start_time)//60, int(start_time)%60)),
            # "Available till": str(datetime.time(int(end_time)//60, int(end_time)%60)),
            # "soc": current_soc,
            "battery_capacity": bcap,
            "connectors": connectorTypes
        }
    existing_requests.append(new_request)
    #updated_requests = pd.concat([new_request, existing_requests[:]]).drop_duplicates().reset_index(drop=True)
    config.REQUESTS = existing_requests

    copy_sched = existing_schedule
    config.SLOT_MAPPING = existing_schedule
    config.CACHE = cache
    config.POSSIBLE_SLOTS = existing_pslots
    flag=0
    if len(cs_queue)==0:
        return json.dumps({"Error":"Scheduling Error", "Message":"No ports given in priority to schedule charging"})
    
    ports_priority = []
    stime = {}; etime={}; soc={}
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
        
        # try:
        #     charging_port = [x for x in charging_stations[cs_key]['chargingPark']['connectors'] if x['id']==portno][0]
        # except:
        #     return json.dumps({"Error":"Index Error", "Message":"Charging station/ports out of index range"})

        begin = helper.roundup(stime[cs_key]); end = etime[cs_key]
        # duration = helper.find_duration(charging_port['ratedPowerKW'], bcap, soc)
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
            config.CACHE[port_id] = config.SLOT_MAPPING[port_id]
            json_object = json.dumps(config.CACHE, indent=4)
            with open("datasets/cache_slots.json","w") as f: f.write(json_object)

            config.SLOT_MAPPING = copy_sched
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
        requests = request_data['requests']

    except:
        return json.dumps({"Success":0,"Error":"Input Data Error", "Message":"Input data not given or not in JSON format"})
    
    cache = json.load(open('datasets/cache_slots.json')) 
    schedule = json.load(open('datasets/slot_mapping.json'))

    for req in requests:
        request_id = req['request_id']
        port_id = req['station_id']+'__'+str(req['port'])
        try:
            schedule[port_id] = cache[port_id]
            del cache[port_id]
        except:
            return json.dumps({"Success":0,"Error":"Index Error", "Message": "Port id not initialized in cache"})
        
    config.SLOT_MAPPING = schedule
    config.CACHE = cache

    json_object = json.dumps(config.SLOT_MAPPING, indent=4)
    with open("datasets/slot_mapping.json","w") as f: f.write(json_object)

    json_object = json.dumps(cache, indent=4)
    with open("datasets/cache_slots.json","w") as f: f.write(json_object)

    return json.dumps({"Success":1, "Message":"Slots confirmed. Success!"})

    
if __name__ == '__main__':
    app.run(debug = True)
