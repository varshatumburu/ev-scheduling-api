import json, datetime, math, sys, os
import pandas as pd

sys.path.insert(1, os.path.join(sys.path[0], 'modules'))
from scheduler import prebooked_scheduling, SLOT_TIME
import helper

sys.path.insert(2, sys.path[0])
import config

global_requests = json.load(open(config.DATASET + "/base_requests.json"))

def roundup(x):
    return int(math.ceil(x / SLOT_TIME)) * int(SLOT_TIME)

graph=dict(); reqSlots = config.REQUIRED_SLOTS
slot_mapping = dict()

def createGraph(requests, port_id="-1", charging_port={}):
	duration = 0
	for req in requests:
		st = roundup(req['start_time'])
		if charging_port:
			duration = helper.find_duration(charging_port['ratedPowerKW'], req['battery_capacity'], req['soc'])
		else: 
			duration = req['duration']
		# nslots = int(math.ceil(duration/SLOT_TIME))
		# reqSlots[req['index']]=nslots

		matchedSlots=[]
		i=1
		while st + duration<=req['end_time']:
			matchedSlots.append(int(st/SLOT_TIME))
			st+=SLOT_TIME; i+=1

		if(port_id=="-1"):
			graph[req['index']]=(matchedSlots)
		else:
			config.POSSIBLE_SLOTS[port_id][req['index']]=(matchedSlots)

	graphs_object = json.dumps(config.POSSIBLE_SLOTS, indent=4)
	with open("datasets/possible_slots.json","w") as f: f.write(graphs_object)
	
def printSchedule(charging_port, request=global_requests, slot_mapping=slot_mapping):

	check=[]
	for key in sorted(slot_mapping.keys()):
		if(slot_mapping[key] in check): continue
		check.append(slot_mapping[key])
		bcap = [req for req in request if req['index']==slot_mapping[key]][0]['battery_capacity']
		dur = helper.find_duration(charging_port['power'], bcap)
		time = datetime.time(int(key*SLOT_TIME)//60, int(key*SLOT_TIME)%60)
		print(f"Request {slot_mapping[key]} scheduled at {time} for {dur} mins.")

def kuhn(request_id, vis=dict(), start_slot=0, slot_mapping=slot_mapping, port_id="-1", shift=[], offline=0):

	if(vis.get(port_id)==None): 
		vis[port_id]=dict()
	elif(vis[port_id].get(request_id)!=None):
		return False
	vis[port_id][request_id]=True

	if config.CHARGING_STATIONS.__len__==0: 
		config.CHARGING_STATIONS = json.load(open('datasets/ev_stations.json'))
	charging_stations = config.CHARGING_STATIONS
	charging_requests = config.REQUESTS
	request = config.REQUESTS[request_id]
	# nslots = reqSlots[request_id] # number of slots required to fit

	# Iterate through all ports in 1 cs, take some sorted order of ports 
	csidx, pidx = "",""
	if port_id=="-1":
		possibleSlots = graph[request_id]
	else:
		csidx, pidx = port_id.split('__')
		ports = charging_stations[csidx]['chargingPark']['connectors']

		duration = helper.find_duration(list(filter(lambda ports: ports['id'] == int(pidx), ports))[0]['ratedPowerKW'], request['battery_capacity'])
		nslots = int(math.ceil(duration/SLOT_TIME))
		possibleSlots = config.POSSIBLE_SLOTS[port_id][request_id]

	if(slot_mapping.get(port_id)==None): slot_mapping[port_id]={}
	for slot in possibleSlots:
		if slot<start_slot:continue

		busy_slots = [val for val in range(slot,slot+nslots) if val in slot_mapping[port_id].keys()]

		if(len(busy_slots)==0):
			config.SCHEDULE_FIT[request_id] = (port_id, slot, nslots)
			for i in range(nslots):
				slot_mapping[port_id][slot+i]=request_id
			return True
		else:
			for bs in busy_slots:
				if not shift:
					shiftable_port_indices = [port["id"] for port in ports\
						if port['connectorType'] in charging_requests[request_id]['connectors'] and port["id"]!=int(pidx)]
					sorted_port_indices = sorted(shiftable_port_indices, key= lambda x: helper.find_duration(ports[x]['ratedPowerKW'], request['battery_capacity']))
					shift = sorted_port_indices

				if(kuhn(slot_mapping[port_id][bs], vis, slot+nslots, slot_mapping, port_id, [], offline)):
					config.SCHEDULE_FIT[request_id] = (port_id, slot, nslots)
					for i in range(nslots):
						slot_mapping[port_id][slot+i]=request_id
					return True
				elif not offline: 
					for sp in shift:
						next_portid = csidx+"__"+str(sp)
						shift_reqid = slot_mapping[port_id][bs]
						shift.remove(sp)
						if config.POSSIBLE_SLOTS.get(next_portid)==None: config.POSSIBLE_SLOTS[next_portid]={}
						config.POSSIBLE_SLOTS[next_portid][shift_reqid] = config.POSSIBLE_SLOTS[port_id][shift_reqid]

						graphs_object = json.dumps(config.POSSIBLE_SLOTS, indent=4)
						with open("datasets/possible_slots.json","w") as f: f.write(graphs_object)

						if(kuhn(shift_reqid, vis, 0, slot_mapping, next_portid, shift)):
							config.SCHEDULE_FIT[request_id] = (port_id, slot, nslots)
							for i in range(nslots):
								slot_mapping[port_id][slot+i]=request_id
							return True

	return False

def init_schedule(reqSet, port_id="-1", slot_mapping = dict(), offline=0):
	if(port_id=="-1"): graph.clear()
	else: config.POSSIBLE_SLOTS[port_id] = {}

	requests = [req for req in global_requests if req['index'] in reqSet]
	cskey= port_id.split('__')[0]; portno= int(port_id.split('__')[1])
	ports = config.CHARGING_STATIONS[cskey]['chargingPark']['connectors']
	charging_port = list(filter(lambda ports: ports['id'] == int(portno), ports))[0]
	selected = prebooked_scheduling(requests, charging_port)
	requests = [req for req in requests if req['index'] in selected]

	createGraph(requests, port_id, charging_port)
	
	slot_mapping[port_id]={}
	for i in [r['index'] for r in requests]:
		visited = dict()
		if(kuhn(i, visited, 0, slot_mapping, port_id,[], offline)): pass

	printSchedule(charging_port, global_requests, slot_mapping[port_id])
	return selected, slot_mapping[port_id]

# Take in dynamic inputs 
def dynamic_requests():
	nreq = len(global_requests)
	idx = max([r['index'] for r in global_requests])+1
	while input("-----------------------\nEnter to go to new request: (-1 to break)")!="-1":
		duration = int(input("Enter duration: "))
		start_time = int(input("Enter start of availability: "))
		end_time = int(input("Enter end time of availability: "))

		global_requests.append({
			"index":idx,
			"duration": duration,
			"start_time": start_time,
			"end_time": end_time
		})

		st = roundup(start_time)
		nslots = int(math.ceil(duration/SLOT_TIME))
		reqSlots[idx]=nslots
		matchedSlots=[]
		while st + duration<=end_time:
			matchedSlots.append(int(st/SLOT_TIME))
			st+=SLOT_TIME

		graph[idx]=(matchedSlots)

		visited=dict()
		if(kuhn(idx, visited)): 
			print("\n>>> REQUEST ACCEPTED! NEW SCHEDULE:")
		else: 
			print("\n>>> REQUEST DENIED. BUSY SCHEDULE.")

		nreq+=1; idx+=1
		printSchedule()

if __name__=='__main__':
	createGraph(global_requests)

	for i in [r['index'] for r in global_requests]:
		visited = dict()
		if(kuhn(i, visited)): pass

	printSchedule()
	dynamic_requests()
