from mcp_test.positions import get_star_position, local_sidereal_and_isotime_calc

import os, sys
from mcp.server import MCPServer
import requests
from datetime import datetime, timedelta, time, timezone

from dotenv import load_dotenv
import base64
import requests_cache
import yaml
from pathlib import Path





load_dotenv()

mcp = MCPServer("star_tracker")
cached = requests_cache.CachedSession('nasa_cache',expire_after=108000)  # caches the photo for half a day
w_cached = requests_cache.CachedSession('weather_cache', expire_after=900)  # cache for weather info
IST_zone = timezone(timedelta(hours=5, minutes=30))  # helpful in calculating the indian time 

def _get_image_of_the_day(date):

    """Gets the image of the day from NASA """

    query_params = {'date':date,
                    'api_key': os.getenv("API_KEY",None)}

    if query_params['api_key'] is None:
        raise KeyError
    
    response = cached.get(url="https://api.nasa.gov/planetary/apod",
                            params=query_params)
    remaining = response.headers.get("X-RateLimit-Remaining")
    print(f"{remaining} attempts left",file=sys.stderr)

    return response.json()

@mcp.tool()
def show_image_of_the_day() -> dict:

    """Displays the NASA apod (Photo/video of the day) with image url or plays the mp4 file
    
        Input args:
            None, but NASA .env key must be present in the environment (current directory in config)
        
        Output args:
            Title: Title of today's Image or Video
            Explanation: Explanation of the image or video 
            type: whether it is an image or video (then it is text)
            data: if its image, then base64 data of the image
            mimetype: if its image, its set
            text: if its a video, it will show the text with the url to play the video
            """

    response = _get_image_of_the_day(datetime.date.today().isoformat())

    result = [{"Title": response["title"], "Explanation": response["explanation"]}]

    if response["media_type"] == "image":
        image_response = requests.get(response['url'])
        base64_data = base64.b64encode(image_response.content).decode("utf-8")
        mime = image_response.headers.get('content-type')
    
        # Return using the image content type
        result.append(
            {
                "type": "image",
                "data": base64_data,
                "mimeType": mime
            })
    else:
        result.append(
        {
            "type": "text",
            "text": f"Here is the video of the day: [Play Video]({response['url']})"
        })
    return result


def _get_location(city:str, state:str, country:str):
    """Gets the given location as latitude and longitude"""

    addy = [city, state, country]

    query_params = {
    "name": ', '.join(addy),
    "count": 1,          # Number of search results to return
    "language": "en",
    "format": "json"}

    response = w_cached.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params=query_params
    )

    response.raise_for_status()
    data = response.json()

    # Extract results array
    results = data.get("results", [])
    for spot in results:  # just running for one as of now
        lat = spot.get("latitude")
        lon = spot.get("longitude")

    return lat, lon

        
@mcp.tool()
def get_weather(city:str, state:str, country:str) -> dict:
    """ Gets the hourly weather forecast of the given location
    
    Input Args:
        city: The city you want the current weather
        state: The state you want the current weather
        country: The country you want the current weather
        
    Output Args: (relevant information)
        latitude: The location's latitude
        longitude: The location's longitude
        utc_offset_seconds: The location's offset from utc (always subtract it with the time to get utc time)
        timezone: The location's timezone
        elevation: The altitude of the location in metre
        current units: Dictionary of the units for the given keys inside for current values (for example, if 'wind_speed_10m': 'km/h', it means wind speed is measured in km/h)
        current: Dictionary of the current values for the given keys with units given above in the current units dictionary for them.( for example, if 'wind_speed_10m': 10.4, it means wind speed is 10.4 km/h)
        daily units: Dictionary of the units for the given keys inside for daily values (day by day) for the next week (for example if 'sunrise': 'iso8601', sunset is measured in iso8601 formatted time)
        daily: Dictionary of the daily values(day by day) for the given keys with units given above in the daily units dictionary for them.
        """
    
    lat, lon = _get_location(city=city, state=state, country=country)  # hardcoded rn, but need to make it dynamic
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["uv_index_max", "sunrise", "sunset", "moonrise", "moonset"],
        "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "wind_speed_10m", "wind_direction_10m", "rain", "precipitation"],
        "timezone": "auto"}
    responses = w_cached.get(url, params = params)
    return responses.json()


def get_cloud_cover(lat: float , lon: float , sunset: datetime, sunrise: datetime, offset_seconds: int):
    # get the latitude and longitude of the observer location

    # need the sunset and sunrise of the current day also offset seconds for time zone aware comparison
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "cloud_cover",
        "timezone": "auto"
    }

    response = w_cached.get(url, params = params)
    data = response.json()

    # dict = {(datetime.fromisoformat(x).day,datetime.fromisoformat(x).hour) : cc for x,cc in zip(data['hourly']['time'], data['hourly']['cloud_cover']) }

    # start = (sunset.day, sunset.hour)
    # end = (sunrise.day, sunrise.hour)

    # cloud_cover = {key:value for key,value in dict.items() if start <= key <= end}
    # the above flow will break for month change for example sunset is at 31st and sunrise on 1st, so using datetime object to compare directly
    # also variable shadowing for the variable dict which overrides built-in dict

    tz = timezone(timedelta(seconds=offset_seconds))  # add this to dt so comaprison can work between timezone aware datetime variables
    # Map datetime object directly
    cloud_dict = {datetime.fromisoformat(t).replace(tzinfo=tz): cc for t, cc in zip(data['hourly']['time'], data['hourly']['cloud_cover'])}

    # Compare directly using datetime objects
    cloud_cover = {(dt.day, dt.hour): cc for dt, cc in cloud_dict.items() if sunset <= dt <= sunrise}
    return cloud_cover


def get_star_hashmaps(lat:float, lon:float, sunset: str) -> list[dict]:
    """ Runs the api for the favorite stars provided in the objects.yml file and returns the
    json response from the requests"""

    star_list = []

    yaml_path = Path("src") / "mcp_test" / "objects.yml"  # compatible with linux, dockers etc. as well
    with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
    
    wanted = {key : set(values) for key,values in data.items()}
    params = {
            "lat": lat,
            "lon": lon,
            "time": sunset
        } 

    stars = [star for star_set in wanted.values() for star in star_set]
    for slug in stars:
        url = f"https://spacecatalog.org/api/v1/objects/{slug.lower()}"
        response = w_cached.get(url,params=params)
        r = response.json()
        star_list.append(r)
    return star_list





@mcp.tool()
def get_stars_and_planets(city:str, state:str, country:str) -> list[dict]:
    """
    Calculates visibility using cloud cover & magnitude, altitude, azimuth, observable windows, and constellation for stars between sunset and sunrise.
    Answers the question, "Which favorite stars/constellations that I can see today and in what time window?"

    Input Args:
        city: The city you're going to watch the stars from
        state: The state in which the city is
        country: THe country in which the state is

    Output Args:
        Each element in the list contains these keys,
        name: Name of the star
        class: Class of the star
        category: Usually a star
        mag: Magnitude of the brightness of the star, lower the value better the visibility
        mag_band: Classification of the magnitude of the brightness
        constellation: The constellation to which the star belongs to
        positions: Dictionary which contains time, altitude angle, azimuth angle, observable, cloud cover, and above horizon for every 15 minute intervals between sunset and sunrise.
            time: ISO format time 
            altitude angle: How high the star is from the horizon (negative values mean below the horizon, positive meaning above the horizon, higher the value better the visibility)
            azimuth angle: In Which direction the star is on the sky (0 means North, 45 means North-east, 90 means East, 135 means South-east, 180 means South, 225 means South-west, 270 means West, 315 means North west and 360 is North once again)
            observable: If the star is observable or not, a boolean value that describes whether a sytar is above 10 degree altitude angle for good visibility
            cloud cover: Magnitude of cloud cover present during that hour in that place, (higher the value harder to see)
            above horizon: Boolean value that describes whether the star is above 0 altitude angle or not, (0 - 10 altitude angle is technically abpove horizon but harder to see due to ground obstructions)
    """

    # get the latitude and longitude of the observer location
    lat, lon = _get_location(city, state, country)

    # need the sunset and sunrise of the current day
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["sunrise", "sunset"],
        "timezone": "auto"}

    response = w_cached.get(url, params = params)
    data = response.json()

    # process the sunset and sunsrise from json output, that is in iso8601 format
    sunset = data['daily']['sunset'][0]  # today's sunset
    sunrise = data['daily']['sunrise'][1]  # tomorrow's sunrise

    offset_seconds = data.get("utc_offset_seconds", 0)  # to subtract to the datetime variables to get UTC time
    tz = timezone(timedelta(seconds=offset_seconds))

    # get the visible objects in the night sky at the given time
    dynamic_list = get_star_hashmaps(lat, lon, sunset)  # need timezone aware sunset time, 
                                                                             # since space catlog assumes any datetime sent as UTC
    

    # convert sunset and sunrise to datetime objects
    sunrise = datetime.fromisoformat(sunrise)
    sunset = datetime.fromisoformat(sunset)
    sunrise = sunrise.replace(tzinfo=tz)  # need this to correctly calculate the gmst 
    sunset = sunset.replace(tzinfo=tz)  # need this to correctly calculate the gmst 

    

    # get cloud cover for the given time range
    cloud_cover = get_cloud_cover(lat, lon, sunset, sunrise, offset_seconds)

    # get the local sidereal time lists and isoformat time for 15 minute intervals from sunset to sunrise
    time_list, lst_list = local_sidereal_and_isotime_calc(sunset, sunrise, lon, offset_seconds)

    # get the viewing time range at night for the stars
    position = get_star_position(dynamic_list, lat, lon, cloud_cover, time_list, lst_list)
    
    return position

    




    


if __name__ == "__main__":
    mcp.run(transport='stdio')