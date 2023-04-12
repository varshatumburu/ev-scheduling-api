import requests
import json

url = 'http://127.0.0.1:5000/confirm'

cs_keys = ['v4BtSzW6bd1j7YfRrWPLyQ',
              'qPjF-ulpKFB5u7Tr3EIwCg',
              'PcXxHxidfrpSUePHXNYb_A',
              '7J3EWh4WAPS0X8QtcpovMQ']

connectors = [
    "StandardHouseholdCountrySpecific",
            "GBT20234Part2",
            "IEC60309AC1PhaseBlue",
            "IEC62196Type3",
            "IEC62196Type2CCS",
            "Chademo",
            "IEC62196Type1",
            "GBT20234Part3",
            "IEC60309DCWhite",
            "IEC62196Type2CableAttached"]

data = {
    'start_time':  [300,350,310], 
	'end_time': [400,450,410], 
	'cs_queue': ["dBK-On6XfGWQECVAxzUyxg","sGVHYoB-UAoUMjhgclYCDw","PcXxHxidfrpSUePHXNYb_A"], 
	'battery_capacity':60,
    'connectors':connectors
}

cdata = {
    'request_id':5,
    'station_id': 'dBK-On6XfGWQECVAxzUyxg',
    'port':'2'
}

headers =  {"Content-Type":"application/json"}
x = requests.post(url, data = json.dumps(cdata), headers=headers)

print(x.text)