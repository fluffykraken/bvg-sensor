# Version History:
# Version 0.1 - initial release
# Version 0.2 - added multiple destinations, optimized error logging
# Version 0.3 fixed encoding, simplified config for direction
# Version 0.3.1 fixed a bug when departure is null
# Version 0.3.2 bufix for TypeError

from urllib.request import urlopen
import json
import pytz
# TODO DEBUG ONLY
import os.path

from datetime import datetime, timedelta
from urllib.error import URLError

import logging
import voluptuous as vol
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA

_LOGGER = logging.getLogger(__name__)

ATTR_STOP_ID = 'stop_id'
ATTR_STOP_NAME = 'stop_name'
ATTR_DUE_IN = 'due_in'
ATTR_DELAY = 'delay'
ATTR_REAL_TIME = 'departure_time'
ATTR_DESTINATION = 'direction'
ATTR_TRANS_TYPE = 'type'
ATTR_TRIP_ID = 'trip'
ATTR_LINE_NAME = 'line_name'

CONF_NAME = 'name'
CONF_STOP_ID = 'stop_id'
CONF_DESTINATION = 'direction'
CONF_MIN_DUE_IN = 'walking_distance'
CONF_CACHE_PATH = 'file_path'

CONNECTION_STATE = 'connection_state'
CON_STATE_ONLINE = 'online'
CON_STATE_OFFLINE = 'offline'

ICONS = {
    'suburban': 'mdi:subway-variant',
    'subway': 'mdi:subway',
    'tram': 'mdi:tram',
    'bus': 'mdi:bus',
    'regional': 'mdi:train',
    'ferry': 'mdi:ferry',
    'express': 'mdi:train',
    'n/a': 'mdi:clock',
    None: 'mdi:clock'
}

SCAN_INTERVAL = timedelta(seconds=60)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_STOP_ID): cv.string,
    vol.Required(CONF_DESTINATION): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_MIN_DUE_IN, default=10): cv.positive_int,
    vol.Optional(CONF_CACHE_PATH, default='/'): cv.string,
    vol.Optional(CONF_NAME, default='BVG'): cv.string
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the sensor platform."""
    stop_id = config[CONF_STOP_ID]
    direction = config.get(CONF_DESTINATION)
    min_due_in = config.get(CONF_MIN_DUE_IN)
    file_path = config.get(CONF_CACHE_PATH)
    name = config.get(CONF_NAME)
    add_entities([Bvgsensor(name, stop_id, direction, min_due_in, file_path, hass)])


class Bvgsensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, name, stop_id, direction, min_due_in, file_path, hass):
        """Initialize the sensor."""
        self._cache_size = 60
        self._cache_creation_date = None
        self._name = name
        self._state = None
        self._stop_id = stop_id
        self.direction = direction
        self.min_due_in = min_due_in
        self.url = "https://1.bvg.transport.rest/stations/{}/departures?duration={}".format(self._stop_id, self._cache_size)
        self.data = None
        self.singleConnection = None
        self.hass_config = hass.config.as_dict()
        self.file_path = self.hass_config.get("config_dir") + file_path
        self.file_name = "bvg_{}.json".format(stop_id)
        self._con_state = {CONNECTION_STATE: CON_STATE_ONLINE}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        if self.singleConnection is not None:
            return {ATTR_STOP_ID: self._stop_id,
                    ATTR_STOP_NAME: self.singleConnection.get(ATTR_STOP_NAME),
                    ATTR_DELAY: self.singleConnection.get(ATTR_DELAY),
                    ATTR_REAL_TIME: self.singleConnection.get(ATTR_REAL_TIME),
                    ATTR_DESTINATION: self.singleConnection.get(ATTR_DESTINATION),
                    ATTR_TRANS_TYPE: self.singleConnection.get(ATTR_TRANS_TYPE),
                    ATTR_LINE_NAME: self.singleConnection.get(ATTR_LINE_NAME)
                    }
        else:
            return {ATTR_STOP_ID: 'n/a',
                    ATTR_STOP_NAME: 'n/a',
                    ATTR_DELAY: 'n/a',
                    ATTR_REAL_TIME: 'n/a',
                    ATTR_DESTINATION: 'n/a',
                    ATTR_TRANS_TYPE: 'n/a',
                    ATTR_LINE_NAME: 'n/a'
                    }

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "min"

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if self.singleConnection is not None:
            return ICONS.get(self.singleConnection.get(ATTR_TRANS_TYPE))
        else:
            return ICONS.get(None)

    def update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self.fetchDataFromURL
        self.singleConnection = self.getSingleConnection(self.direction, self.min_due_in, 0)
        if self.singleConnection is not None and len(self.singleConnection) > 0:
            self._state = self.singleConnection.get(ATTR_DUE_IN)
        else:
            self._state = 'n/a'

# only custom code beyond this line
    @property
    def fetchDataFromURL(self):
        try:
            with urlopen(self.url) as response:
                source = response.read()
                self.data = json.loads(source)
                if self._con_state.get(CONNECTION_STATE) is CON_STATE_OFFLINE:
                    _LOGGER.warning("Connection to BVG API re-established")
                    self._con_state.update({CONNECTION_STATE: CON_STATE_ONLINE})
                # write the response to a file for caching if connection is not available, which seems to happen from time to time
                try:
                    with open("{}{}".format(self.file_path, self.file_name), 'w') as fd:
                        # self.data = json.load(fd)
                        json.dump(self.data, fd, ensure_ascii=False)
                        # json.writes(response)
                        self._cache_creation_date = datetime.now(pytz.timezone(self.hass_config.get("time_zone")))
                except IOError as e:
                    _LOGGER.error("Could not write file. Please check your configuration and read/write access for path:{}".format(self.cachePath))
                    _LOGGER.error("I/O error({}): {}".format(e.errno, e.strerror))
        except URLError as e:
            if self._con_state.get(CONNECTION_STATE) is CON_STATE_ONLINE:
                _LOGGER.debug(e)
                _LOGGER.warning("Connection to BVG API lost, using local cache instead")
                self._con_state.update({CONNECTION_STATE: CON_STATE_OFFLINE})
            self.fetchDataFromFile()

    def fetchDataFromFile(self):
        try:
            with open("{}{}".format(self.file_path, self.file_name), 'r') as fd:
                self.data = json.load(fd)
        except IOError as e:
            _LOGGER.error("Could not read file. Please check your configuration and read/write access for path: {}".format(self.cachePath))
            _LOGGER.error("I/O error({}): {}".format(e.errno, e.strerror))

    def getSingleConnection(self, direction, min_due_in, nmbr):
        timetable_l = list()
        date_now = datetime.now(pytz.timezone(self.hass_config.get("time_zone")))
        for dest in direction:
            for pos in self.data:
                # _LOGGER.warning("conf_direction: {} pos_direction {}".format(direction, pos['direction']))
                # if pos['direction'] in direction:
                if dest in pos['direction']:
                    if pos['when'] is None:
                        continue
                    dep_time = datetime.strptime(pos['when'][:-6], "%Y-%m-%dT%H:%M:%S.%f")
                    dep_time = pytz.timezone('Europe/Berlin').localize(dep_time)
                    delay = (pos['delay'] // 60) if pos['delay'] is not None else 0
                    departure_td = dep_time - date_now
                    # check if connection is not in the past
                    if departure_td > timedelta(days=0):
                        departure_td = (departure_td.seconds // 60)
                        if departure_td >= min_due_in:
                            timetable_l.append({ATTR_DESTINATION: pos['direction'], ATTR_REAL_TIME: dep_time,
                                                ATTR_DUE_IN: departure_td, ATTR_DELAY: delay,
                                                ATTR_TRIP_ID: pos['trip'], ATTR_STOP_NAME: pos['stop']['name'],
                                                ATTR_TRANS_TYPE: pos['line']['product'], ATTR_LINE_NAME: pos['line']['name']
                                                })
                            _LOGGER.debug("Connection found")
                        else:
                            _LOGGER.debug("Connection is due in under {} minutes".format(min_due_in))
                    else:
                        _LOGGER.debug("Connection lies in the past")
                else:
                    _LOGGER.debug("No connection for specified direction")
            try:
                _LOGGER.debug("Valid connection found")
                _LOGGER.debug("Connection: {}".format(timetable_l))
                return(timetable_l[int(nmbr)])
            except IndexError as e:
                if self.isCacheValid:
                    _LOGGER.warning("No valid connection found for sensor named {}. Please check your configuration.".format(self.name))
                else:
                    _LOGGER.warning("No up to date data found. API may be down for longer than {} minutes.".format(self._cache_size))
                    _LOGGER.error(e)
                return None

    @property
    def isCacheValid(self):
        date_now = datetime.now(pytz.timezone(self.hass_config.get("time_zone")))
        # If there is no connection right from the start
        if self._cache_creation_date is None:
            self._cache_creation_date = datetime.fromtimestamp(os.path.getmtime("{}{}".format(self.file_path, self.file_name)))
        td = self._cache_creation_date - date_now
        td = td.seconds
        _LOGGER.debug("td is: {}".format(td))
        if td > (self._cache_size * 60):
            _LOGGER.debug("Cache Age (not valid): {}".format(td // 60))
            return False
        else:
            return True
