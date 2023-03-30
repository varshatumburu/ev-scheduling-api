import math, sys

sys.path.insert(1, '/home/varsha_1901cs69/btp/scheduling/modules')
import config, matching
from scheduler import SLOT_TIME

def roundup(x):
    return int(math.ceil(x / SLOT_TIME)) * int(SLOT_TIME)

def find_duration(port_power, battery_capacity, power_factor=0.8):
    return math.ceil(battery_capacity/(port_power*power_factor))

def mapRequests2Ports(nreq, nearest_ports):
    reqMapping = dict()
    for i in range(nreq):
        st=-1
        if not nearest_ports[i].empty():
            st = nearest_ports[i].get()
            if reqMapping.get(st)==None or len(reqMapping[st])==0:
                reqMapping[st]=[]

        if(st!=-1): reqMapping[st].append(i)

    return reqMapping

def iterative_scheduling(nreq, blocked, leftover, reqMapping, nearest_ports, offline):
    iter=0; prev=-1
    # print(reqMapping)
    while len(blocked)!=nreq and prev!=len(blocked) and reqMapping:
        print(f"\n>>> Iteration {iter} >>> ")
        for port in list(reqMapping.keys()):
            prev=len(blocked)
            
            reqidx = reqMapping[port]
            if len(reqidx)==0: continue
            print(f"\nSchedule for Port {port}:")

            selected, config.SLOT_MAPPING[port] = matching.init_schedule(reqidx, port, dict(), offline)
            leftover = list(set(reqidx)-set(selected))

            for lr in leftover:
                if not nearest_ports[lr].empty():
                    next_nearest_port = nearest_ports[lr].get()
                    reqMapping[port].remove(lr)
                    if reqMapping.get(next_nearest_port)==None or len(reqMapping[next_nearest_port])==0:
                        reqMapping[next_nearest_port]=[]
                    reqMapping[next_nearest_port].append(lr)

            blocked = set(list(blocked)+list(selected))

        if(prev==len(blocked)): break
        iter+=1

    print("\nCompleted scheduling!")

# def get_nearest_cs_pq(x, y, max_distance=math.inf):
#     q = PriorityQueue()
#     stations = config.CHARGING_STATIONS
#     for j in range(len(stations)): 
#         # n1, n2 nearest node to x, y in graph (estimation done from there)
#         [n1, n2] = ox.distance.nearest_nodes(config.GRAPH,[x,config.X_NODES[stations.loc[j]["node"]]], [y,config.Y_NODES[stations.loc[j]["node"]]])
#         try:
#             dist = nx.shortest_path_length(config.GRAPH, n1, n2, weight='length')
#             if dist <= max_distance :
#                 q.put((dist,j))
#         except nx.exception.NetworkXNoPath:
#             continue
#     return q

def get_nearest_ports_pq(request, nearest_cs):
    q = Queue()
    stations = config.CHARGING_STATIONS

    while not nearest_cs.empty():
        dist, station_index = nearest_cs.get()
        sorted_ports = sorted(stations.loc[station_index]["ports"], key = lambda x:len(x["vehicles"]))
        for port in sorted_ports:
            duration = find_duration(port["power"], request["battery_capacity"])
            if request["vehicle_type"] in port["vehicles"] and duration<=request["end_time"]-request["start_time"]:
                port_id = str(station_index)+"p"+str(port["id"])
                q.put(port_id)
                
    return q
