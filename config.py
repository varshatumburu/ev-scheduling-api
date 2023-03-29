# contains all the configurable variables to maintain state of user

import pandas as pd
from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="Slot Scheduling App")

CENTER = None
CHARGING_STATIONS=pd.DataFrame()
CS_DROPDOWN = pd.DataFrame(columns = ['label','value'])
CS_NODES = []
CS_POSITIONS = []
COLUMNS = []
DATASET = "/home/varsha_1901cs69/btp/scheduling/datasets"
GRAPH = None
LOCATION = geolocator.geocode("India",timeout=None)
N_CLICKS = 0
NEAREST_CS = dict()
NEAREST_PORTS = dict()
POLYGON = []
PORTS_DROPDOWN = pd.DataFrame(columns = ['label','value'])
POSITIONS = 0
POSSIBLE_SLOTS = dict()
REQUESTS = pd.DataFrame()
REQUESTS_DROPDOWN = pd.DataFrame(columns = ['label','value'])
REQUEST_MAPPING = dict()
REQUEST_NODES = []
REQUIRED_SLOTS = dict()
SCHED_CLICKS = 0
SLOT_MAPPING = dict()
TOTAL_NODES = 0
TOTAL_STATIONS = 0
VISITED = dict()
W2_PORTS = []
W3_PORTS = []
W4_PORTS = []
X_NODES = []
Y_NODES = []
ZOOM_LEVEL = 0
