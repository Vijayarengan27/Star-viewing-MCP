import datetime
from datetime import timedelta, datetime
import math

def local_sidereal_and_isotime_calc(sunset:datetime, sunrise:datetime, longitude:float, offset_seconds: int):
    """Calculates the local sidereal and iso format time for the 15 minute intervals separately and 
    returns both lists"""

    current = sunset
    end = sunrise
    time_list = []  # time list for checking time
    lst_list = []  # local sidereal time list for evry 15 minutes

    while current <= end:

        year = current.year
        month = current.month

        if month <= 2:
            year -= 1
            month += 12

        day = current.day + (current.hour / 24) + (current.minute / 1440) + (current.second / 86400)  # caculate day variable that gives you the amount of day progressed so far
        utc_day = day - (offset_seconds / 86400)

        A = year // 100
        B = 2 - A + (A//4)

        JD = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + utc_day + B - 1524.5  # Julian Date calculation always for utc

        # calculate the Julian time in centuries since JD 2000.0
        T = (JD - 2451545) / 36525

        # caculate greenwich mean sidereal time in degrees
        gmst_deg = 280.46061837 + (360.98564736629 * (JD - 2451545)) + (0.000387933 * (T ** 2)) - ((T ** 3)/ 38710000)

        # normalize it
        gmst_deg %= 360

        # local sidereal time in degrees and normalized
        lst = (gmst_deg + longitude) % 360

        time_list.append(current)
        lst_list.append(lst)

        if current == end:  # if we already reach end (sunrise), we break the loop
            break

        current = min(current + timedelta(minutes=15), end)  # either 15 minute interval or the sunrise, whichever arrives early

    return time_list, lst_list


def get_star_position(stars: list[dict], latitude: float, longitude: float, cloud_cover: dict, time_list: list, lst_list: list) -> list[dict]:
    """ Calculates the relative positions of the stars and charts the movement of them for the
    entire night time for a particular location and returns a relevant hashmap including altitude angle and azimuth angle
    for every 15 minute interval"""

    # using date and time, calculate greenwich sidereal time and using the longitude, calculate the local
    # sidereal time, then using right ascension, find the hour angle,
    # then using hour angle, latitude and the declination angle, start finding the local paramters of the star
    # altitude and azimuth angles, do this for tmie interval of your choice.

    # flow of the function -> calculate time stamps for every 15 minutes from sunset to sunrise and then caculate and store
    # local sidereal time for those intervals and for every star caculate the altitude and azimuth anagles from observer position
    # add extra info regarding the first observable and last observable times, cloud cover and above or below horizon.
    
    
    star_hashmaps = []
    for star in stars:
        if star.get('error', None) is not None:  # if there is an error in getting the slug information, we skip
            continue

        right_ascension = star.get('ra_deg', None)

        # get declination of the star - range [-90, 90], no need to normalize here
        declination = star.get('dec_deg', None)
        declination_rad = math.radians(declination)  # used in radians in the altitude angle calculation
        latitude_rad = math.radians(latitude)  # used un radians for altitude angle caculation

        positional_observation = []
        star_info = {}
        required_fields = ['name', 'class', 'category', 'mag', 'mag_band', 'constellation']
        first_obs = None
        last_obs = None

        for i in range(len(lst_list)):

            lst = lst_list[i]  # easier for indexing normal time too

            # Hour angle in degrees for each star and normalized
            H = (lst - right_ascension) % 360

            # altitude angle calculation, convert relevant hour angle to radians and then calculate altitude angle and then convert back to degrees
            H_rad = math.radians(H)

            sin_h_rad = math.sin(latitude_rad) * math.sin(declination_rad) + (math.cos(latitude_rad) * math.cos(declination_rad) * math.cos(H_rad))
            sin_h_rad = max(-1.0, min(1.0, sin_h_rad))
            h_rad = math.asin(sin_h_rad)

            # Now back to degree convention
            h = math.degrees(h_rad)

            # same for azimuth calculation
            azimuth_rad = math.atan2(-math.sin(H_rad) * math.cos(declination_rad),
                                    math.sin(declination_rad) * math.cos(latitude_rad)
                                    - math.cos(declination_rad) * math.sin(latitude_rad) * math.cos(H_rad)
                                )

            azimuth = math.degrees(azimuth_rad + 360) % 360

            position = {}
            position['time'] = time_list[i].isoformat()
            position['altitude'] = h
            position['azimuth'] = azimuth
            position['observable'] = False  # default will be changed if altitude is greater than 10 degrees
            position['cloud cover'] = cloud_cover.get((time_list[i].day, time_list[i].hour), 'No information available')


            # observable and above horizon logic
            if h >= 0:
                position['above_horizon'] = True
                if h >= 10:
                    position['observable'] = True
            else:
                position['above_horizon'] = False


            # first and last observable times
            if position['observable']:
                if first_obs is None:
                    first_obs = position['time']
                last_obs = position['time']  # Continuously update last_obs while observable

            
            positional_observation.append(position)
                
        for field in required_fields:
            star_info[field] = star.get(field, "N/A")

        star_info["positions"] = positional_observation
        star_info["first observable time"] = first_obs if first_obs else "No information"
        star_info["last observable time"] = last_obs if last_obs else "No information"

        star_hashmaps.append(star_info)
            
    return star_hashmaps










        

if __name__ == "__main__":
    get_star_position([],0,0)

