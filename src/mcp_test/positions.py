import datetime
import math

def get_star_position(stars: list[dict], latitude: int, longitude: int):
    """ Calculates the relative positions of the stars and charts the movement of them for the
    entire night time for a particular location"""

    # using date and time, calculate greenwich sidereal time and using the longitude, calculate the local
    # sidereal time, then using right ascension, find the hour angle,
    # then using hour angle, latitude and the declination angle, start finding the local paramters of the star
    # altitude and azimuth angles, do this for tmie interval of your choice.

    utc = datetime.datetime.now(datetime.UTC)

    year = utc.year
    month = utc.month
    day = utc.day
    time = str(utc.time()).split(':')

    if month <= 2:
        year -= 1
        month += 12

    s = 3600  # total seconds in an hour
    d = 0  # rest of the current day variable

    for t in time:
        d += (float(t) * s)
        s //= 60

    day += (d/(3600*24))  # total days

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

    # Hour angle in degrees for each star and normalized
    right_ascension = stars.get('ra_deg', None)
    H = (lst - right_ascension + 180) % 360 - 180

    # get declination of the star - range [-90, 90], no need to normalize here
    declination = stars.get('dec_deg', None)

    # altitude angle calculation, convert relevant angles to radians and then calculate altitude angle and then convert back to degrees
    latitude_rad = math.radians(latitude)
    declination_rad = math.radians(declination)
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

    print(f"UTC: {utc}")
    print(f"JD: {JD}")
    print(f"GMST: {gmst_deg}")
    print(f"LST: {lst}")
    print(f"RA: {right_ascension}")
    print(f"H: {H}")

    return h, azimuth










        

if __name__ == "__main__":
    get_viewing_time([],0,0)

