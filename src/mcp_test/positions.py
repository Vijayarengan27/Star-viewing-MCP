import datetime
from datetime import timedelta, datetime
import math

def get_star_position(stars: list[dict], latitude: float, longitude: float, sunset: datetime, sunrise: datetime, cloud_cover: dict) -> list[dict]:
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
        

        A = year // 100
        B = 2 - A + (A//4)

        JD = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + B - 1524.5  # Julian Date

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

        current = min(current + timedelta(minutes=15), end)  # either 15 minute interval or the sunrise, whichebver arrives early

    for star in stars:

        right_ascension = star.get('ra_deg', None)

        # get declination of the star - range [-90, 90], no need to normalize here
        declination = star.get('dec_deg', None)
        declination_rad = math.radians(declination)  # used in radians in the altitude angle calculation
        latitude_rad = math.radians(latitude)  # used un radians for altitude angle caculation

        positional_observation = []
        first, last = None, None

        for i in range(len(lst_list)):

            lst = lst_list[i]  # easier for indexing normal time too

            # Hour angle in degrees for each star and normalized
            H = (lst - right_ascension + 180) % 360 - 180

            # altitude angle calculation, convert relevant hour angle to radians and then calculate altitude angle and then convert back to degrees
            H_rad = math.radians(H)

            h_rad = math.asin(math.sin(latitude_rad) * math.sin(declination_rad) + (math.cos(latitude_rad) * math.cos(declination_rad) * math.cos(H_rad)))

            # Now back to degree convention
            h = math.degrees(h_rad)

            # same for azimuth calculation
            azimuth_rad = math.atan2(-math.sin(H_rad) * math.cos(declination_rad),
                                    math.sin(declination_rad) * math.cos(latitude_rad)
                                    - math.cos(declination_rad) * math.sin(latitude_rad) * math.cos(H_rad)
                                )

            azimuth = math.degrees(azimuth_rad) % 360

            position = {}
            position['time'] = time_list[i].isoformat()
            position['altiude'] = h
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
                if first is None:
                    first = time_list[i].isoformat()
            else:
                if first is not None and last is None:
                    last = time_list[i].isoformat()

            


            positional_observation.append(position)
                

        star["positions"] = positional_observation
        if first is None:
            star["first observable time"] = "No information"
        else:
            star["first observable time"] = first

        if last is None:
            star["last observable time"] = "No information"
        else:
            star["last observable time"] = last
            
    return stars










        

if __name__ == "__main__":
    get_star_position([],0,0)

