# weighted job scheduling
from functools import total_ordering
import math

SLOT_TIME = 10

@total_ordering
class Job:
	def __init__(self, index, start, end, duration):
		self.start = start
		self.end = end
		self.index = index
		self.duration = duration

	def __repr__(self) -> str:
		return "{"+str(self.index)+","+str(self.start)+"-"+str(self.end)+"}"

	def __lt__(self, other: object) -> bool:
		return self.end< other.end

def find_duration(port_power, battery_capacity, power_factor=0.8):
    return math.ceil(battery_capacity/(port_power*power_factor))

def optimalNonConflict(arr, i, vis , sorted_list):
	for j in sorted_list:
		if(arr[j[2]].end <= arr[i].start and (arr[i].index not in vis[j[2]])):
			return j[2]
		
	return -1

def optimize(jobs):
	n=len(jobs)
	# print(jobs)
	total_time = [0] * n; global_dp = [0] * n
	total_time[0]=jobs[0].duration 
	global_dp[0]=total_time[0]

	vis = {x:set() for x in range(0,n)}
	gdp_vis = {x:set() for x in range(0,n)}
	used = {y:[] for y in range(0,n)}

	vis[0].add(jobs[0].index)
	gdp_vis[0].add(jobs[0].index)
	used[0].append(0)

	sl = list()
	sl.append(tuple([global_dp[0],1,0]))

	idx=0
	for i in range(1, n):

		dur = jobs[i].duration 
		l = optimalNonConflict(jobs, i, vis, sl)

		# Add to duration if non-overlapping slot is found 
		if l!=-1:
			if jobs[i].index in vis[l]: 
				continue
			dur += total_time[l]
			vis[i]=vis[l].copy()
			used[i]=used[l].copy()

		total_time[i]=dur
		vis[i].add(jobs[i].index)
		used[i].append(i)

		if(total_time[i]>global_dp[i-1] or (total_time[i]==global_dp[i-1] and len(vis[i])>len(gdp_vis[i-1]))):
			global_dp[i]=total_time[i]
			gdp_vis[i]=vis[i]
			idx=i
		else:
			global_dp[i]=global_dp[i-1]
			gdp_vis[i]=gdp_vis[i-1]

		sl.append(tuple([global_dp[i], len(vis[i]), i]))
		sl.sort(reverse=True)

	return used[idx]


def prebooked_scheduling(requests, port):

	permuted_jobs = []
	for r in requests:
		interval = find_duration(port['power'], r['battery_capacity'])
		s = math.ceil(r['start_time']/SLOT_TIME) * SLOT_TIME

		for start in range(s, r['end_time'], SLOT_TIME):
			if(start+interval > r['end_time']): break
			permuted_jobs.append(Job(r['index'], start, start+interval, interval))

	permuted_jobs=sorted(permuted_jobs)
	used_intervals=[]
	if len(permuted_jobs)!=0:
		used_intervals = optimize(permuted_jobs)

	scheduled_job_indices = [permuted_jobs[interval].index for interval in used_intervals]
	return scheduled_job_indices
