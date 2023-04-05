import requests
import json

url = 'http://127.0.0.1:5000'

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
    'start_time': 600, 
	'end_time': 650, 
	'cs_queue': cs_keys, 
    'soc':10, 
	'battery_capacity':60,
    'connectors':connectors
}
headers =  {"Content-Type":"application/json"}
x = requests.post(url, data = json.dumps(data), headers=headers)

print(x.text)