import requests
import json

url = 'http://127.0.0.1:5000'
cs_indices = ['3p0','1p0','1p3','1p2','0p0','3p0','4p1','4p0','5p0','7p1','6p0']

data = {
    'start_time': 600, 
	'end_time': 610, 
	'cs_queue': cs_indices, 
    'soc':10, 
    'vehicle_type':'4w',
	'battery_capacity':60,
    'mileage':300
}
headers =  {"Content-Type":"application/json"}
x = requests.post(url, data = json.dumps(data), headers=headers)

print(x.text)