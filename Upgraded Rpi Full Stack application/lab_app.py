from flask import Flask, request, render_template
import time
import arrow
from datetime import datetime, timedelta
import sqlite3
import sys
import smbus2
import bme280
import board
import plotly.graph_objects as go
from twilio.twiml.messaging_response import MessagingResponse
import os
import subprocess

port = 1
address = 0x76
bus = smbus2.SMBus(port)

calibration_params = bme280.load_calibration_params(bus, address)

app         = Flask(__name__)
app.debug   = True # Make this False if you are no longer debugging

@app.route("/")
def hello():
    return "Hello World! rpi4. </br></br>Get <a href='/lab_temp'> current sensor readings</a> on the Raspberry Pi."

@app.route("/lab_temp")
def lab_temp():
    print("Getting a sensor reading")
    data        = bme280.sample(bus, address, calibration_params)
    temperature = data.temperature
    humidity    = data.humidity
    pressure    = data.pressure
    print("Generating page from template")
    if humidity is not None and temperature is not None and pressure is not None:
        return render_template("lab_temp.html",temp=temperature,hum=humidity,press=pressure)
    else:
        return render_template("no_sensor.html")

@app.route("/lab_env_db", methods=['GET'])  #Add date limits in the URL #Arguments: from=2015-03-04&to=2015-03-05
def lab_env_db():
	temperatures, humidities, pressures, combined_list, timezone, from_date_str, to_date_str, sensor_id, request_string = get_records()

	# Create new record tables so that datetimes are adjusted back to the user browser's time zone.
	time_adjusted_temperatures = []
	time_adjusted_humidities   = []
	time_adjusted_pressure     = []
	time_adjusted_combined     = []

	for record in temperatures:
            local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss").to(timezone)
            time_adjusted_temperatures.append([local_timedate.format('YYYY-MM-DD HH:mm:ss'), round(record[2],2)])

	for record in humidities:
            local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss").to(timezone)
            time_adjusted_humidities.append([local_timedate.format('YYYY-MM-DD HH:mm:ss'), round(record[2],2)])
    
	for record in pressures:
            local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss").to(timezone)
            time_adjusted_pressure.append([local_timedate.format('YYYY-MM-DD HH:mm:ss'), round(record[2],2)])

	record_counter = 0
	for record in combined_list:
            local_timedate = arrow.get(record[1], "YYYY-MM-DD HH:mm:ss").to(timezone)
            time_adjusted_combined.append([record_counter, local_timedate.format('YYYY-MM-DD HH:mm:ss'), round(record[2],2),round(record[3],2),round(record[4],2)])
            record_counter = record_counter + 1

	print("rendering lab_env_db.html with: %s, %s, %s, sensor_id %s" % (timezone, from_date_str, to_date_str, sensor_id))

	return render_template("lab_env_db.html",	timezone		= timezone,
							temp 			= time_adjusted_temperatures,
							hum 			= time_adjusted_humidities,
                                                        press                   = time_adjusted_pressure,
                                                        combined                = time_adjusted_combined,
                                                        combined_items          = len(combined_list),
							from_date 		= from_date_str,
							to_date 		= to_date_str,
                                                        temp_items              = len(temperatures),
                                                        hum_items               = len(humidities),
                                                        press_items             = len(pressures),
                                                        sensorid                = sensor_id,
			                                query_string            = request.query_string.decode('utf-8'))


@app.route("/sms", methods=['GET', 'POST'])
def sms_reply():
    MY_PERSONAL_PHONE_NUMBER = os.environ["MY_PHONE_NUMBER"]
    SMS_BODY = 'Body'
    SMS_FROM = 'From'
    resp = MessagingResponse()
    print("My number: %s", MY_PERSONAL_PHONE_NUMBER)
    print("Request values: %s", request.values)
    if request.values[SMS_FROM] == MY_PERSONAL_PHONE_NUMBER:
        command = request.values[SMS_BODY].lower().strip()

        if command == 'commands':
            resp_msg_str = ''
            resp_msg_str += 'status <sensor #>: get sensor status\n'
            resp_msg_str += 'ip: get IP addresses\n'
            resp_msg_str += 'reboot: reboot device\n'
            resp_msg_str += 'shutdown: shutdown device\n'
            resp.message(resp_msg_str)
        elif command == 'ip':
            ip_address = subprocess.check_output("hostname -I", shell=True).decode('utf-8').replace(' ', '\n')
            resp.message(ip_address)
        elif command == 'reboot':
            subprocess.call('sudo reboot now', shell=True)
            # No need to respond
        elif command == 'shutdown':
            subprocess.call('sudo shutdown now', shell=True)
            # No need to respond
        else:
            command_items = command.split()

            if command_items[0] == 'status':
                if len(command_items) == 2:
                    # Get sensor number
                    sensor_id = None

                    try:
                        sensor_id = int(command_items[1])
                    except:
                        resp.message('Invalid sensor ID')

                    if sensor_id is not None:
                        temperature, humidity = get_last_record(sensor_id)

                        if humidity is not None and temperature is not None:
                            deg_sign = u"\N{DEGREE SIGN}"
                            resp_msg_str = f'Device {sensor_id} reported a temperature of {temperature}{deg_sign}C and {humidity}% humidity.'
                        else:
                            resp_msg_str = f'No data available for sensor ID {sensor_id} in the last hour.'

                        resp.message(resp_msg_str)
                else:
                    resp.message('Too many parameters for status command')
            else:
                resp.message('Invalid command')

        return str(resp)
    else:
        # Ignore text messages from other mobile phone numbers.
        return None

def get_records():
    request_string  = request.query_string
    yesterday       = datetime.today() - timedelta(days=1)
    from_date_str   = request.args.get('from',yesterday.strftime("%Y-%m-%d %H:%M"))  #Get the from date value from the URL, or use the start of day today UTC
    to_date_str     = request.args.get('to',time.strftime("%Y-%m-%d %H:%M"))   #Get the to date value from the URL, or use now UTC
    timezone 	    = request.args.get('timezone','Etc/UTC')                      #Get the timezone, or use UTC
    range_h_form    = request.args.get('range_h','')                              #This will return a string, if field range_h exists in the request
    range_h_int     = "nan"  #initialise this variable with not a number
    sensor_id       = request.args.get('sensor_id','1')                           #Get the sensor ID, or fall back to 1

    print ("REQUEST:")
    print (request.args)

    try:
        range_h_int     = int(range_h_form)
    except:
        print ("range_h_form not a number")

    print ("Received from browser: From: %s, To: %s, Timezone: %s, Range: %s, Sensor_id: %s" % (from_date_str, to_date_str, timezone, range_h_int, sensor_id))

    if not validate_date(from_date_str):			# Validate date before sending it to the DB
        from_date_str 	= time.strftime("%Y-%m-%d 00:00")
    if not validate_date(to_date_str):
        to_date_str 	= time.strftime("%Y-%m-%d %H:%M")		# Validate date before sending it to the DB

    print ("Time adjusted: From: %s, To: %s, Timezone: %s, Range: %s, Sensor_id: %s" % (from_date_str, to_date_str, timezone, range_h_int, sensor_id))

    # Create datetime object so that we can convert to UTC from the browser's local time
    from_date_obj       = datetime.strptime(from_date_str,'%Y-%m-%d %H:%M')
    to_date_obj         = datetime.strptime(to_date_str,'%Y-%m-%d %H:%M')

    # If range_h is defined, we don't need the from and to times
    if isinstance(range_h_int,int):
        arrow_time_from = arrow.utcnow().shift(hours=-range_h_int)
        arrow_time_to   = arrow.utcnow()
        from_date_utc   = arrow_time_from.strftime("%Y-%m-%d %H:%M")
        to_date_utc     = arrow_time_to.strftime("%Y-%m-%d %H:%M")
        from_date_str   = arrow_time_from.to(timezone).strftime("%Y-%m-%d %H:%M")
        to_date_str	= arrow_time_to.to(timezone).strftime("%Y-%m-%d %H:%M")
    else:
	#Convert datetimes to UTC so we can retrieve the appropriate records from the database
        from_date_utc   = arrow.get(from_date_obj, timezone).to('Etc/UTC').strftime("%Y-%m-%d %H:%M")
        to_date_utc     = arrow.get(to_date_obj, timezone).to('Etc/UTC').strftime("%Y-%m-%d %H:%M")

    print("From UTC: ", from_date_utc)
    print("To UTC: ", to_date_utc)
    print("From: ", from_date_str)
    print("To: ", to_date_str)

    conn 			    = sqlite3.connect('/var/www/lab_app/lab_app.db')
    curs 			    = conn.cursor()
    temp_sql = "SELECT * FROM temperatures WHERE (rDateTime BETWEEN '%s' AND '%s') AND sensorID = %s" % (from_date_utc.format('YYY-MM-DD HH:mm'), to_date_utc.format('YYY-MM-DD HH:mm'), sensor_id)
    #curs.execute("SELECT * FROM temperatures WHERE (rDateTime BETWEEN '2020-01-26 00:00' AND '2020-01-26 05:50') AND sensorID = 3")
    #curs.execute("SELECT * FROM temperatures WHERE sensorID = ? AND (rDateTime BETWEEN ? AND ?)", (sensor_id, from_date_utc.format('YYYY-MM-DD HH:mm'), to_date_utc.format('YYYY-MM-DD HH:mm')))
    print(temp_sql)
    curs.execute(temp_sql)
    temperatures 	    = curs.fetchall()
    print("Temperatures:")
    print(temperatures)
    #curs.execute("SELECT * FROM humidities WHERE (rDateTime BETWEEN '2020-01-26 00:00' AND '2020-01-26 05:50') AND sensorID = 3")
    curs.execute("SELECT * FROM humidities WHERE sensorID = ? AND (rDateTime BETWEEN ? AND ?)", (sensor_id, from_date_utc.format('YYYY-MM-DD HH:mm'), to_date_utc.format('YYYY-MM-DD HH:mm')))
    humidities 		    = curs.fetchall()
    curs.execute("SELECT * FROM pressures WHERE (rDateTime BETWEEN ? AND ?) AND sensorID = ?", (from_date_utc.format('YYYY-MM-DD HH:mm'), to_date_utc.format('YYYY-MM-DD HH:mm'), sensor_id))
    print("SELECT * FROM pressures WHERE (rDateTime BETWEEN ? AND ?) AND sensorID = ?", (from_date_utc.format('YYYY-MM-DD HH:mm'),to_date_utc.format('YYYY-MM-DD HH:mm'), sensor_id))
    pressures = curs.fetchall()
    print("Pressures:")
    print(pressures)
    conn.close()

    # This code will combine the three lists into one
    combined_list = []
    for x, temp in enumerate(temperatures):
       #print(x,",",temperatures[x][0],",",humidities[x][2],",",pressure[x][2])
       if len(temperatures) > x:
         combined_temp = temperatures[x][2]
         combined_date = temperatures[x][0]
       else:
         combined_temp = -999
         combine_date = "-"
       if len(humidities) > x:
         combined_humidity = humidities[x][2]
       else:
         combined_humidity = -999
       if len(pressures) > x:
         combined_pressure = pressures[x][2]
       else:
         combined_pressure = -999
    #      print(x,",",temperatures[x][0])
       combined_list.append([x,combined_date,combined_temp,combined_humidity,combined_pressure])
    print("Combined list:")
    print(combined_list)
    return [temperatures, humidities, pressures, combined_list, timezone, from_date_str, to_date_str, sensor_id, request_string.decode()]

@app.route("/to_plotly", methods=['GET'])  #This method will send the data to ploty.
def to_plotly():
      temperatures, humidities, pressures, combined_list, timezone, from_date_str, to_date_str, sensor_id, request_string = get_records()
        
      # Create new record tables so that datetimes are adjusted back to the user browser's time zone.
      time_series_adjusted_temperature  = []
      time_series_adjusted_humidity           = []
      time_series_adjusted_pressure           = []
      time_series_temperature_values      = []
      time_series_humidity_values              = []
      time_series_pressure_values              = []

      for record in temperatures:
            local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss").to(timezone)
            time_series_adjusted_temperature.append(local_timedate.format('YYYY-MM-DD HH:mm:ss'))
            time_series_temperature_values.append(round(record[2],2))

      for record in humidities:
            local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss").to(timezone)
            time_series_adjusted_humidity.append(local_timedate.format('YYYY-MM-DD HH:mm:ss'))   #Best to pass datetime in text so that Plotly respects it
            time_series_humidity_values.append(round(record[2],2))

      for record in pressures:
            local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss").to(timezone)
            time_series_adjusted_pressure.append(local_timedate.format('YYYY-MM-DD HH:mm:ss'))
            time_series_pressure_values.append(round(record[2],2))

      fig_temp = go.Figure()
      fig_temp.add_trace(go.Scatter(x=time_series_adjusted_temperature,y=time_series_temperature_values,name="Temperature",line=dict(color='firebrick', width=4)))
      fig_temp.update_layout(title="Temperature in Peter's lab", xaxis_title="Date",yaxis_title="Temperature (degrees Celsius)")
      
      fig_hum = go.Figure()
      fig_hum.add_trace(go.Scatter(x=time_series_adjusted_humidity,y=time_series_humidity_values,name="Humidity",line=dict(color='firebrick', width=4)))
      fig_hum.update_layout(title="Humidity in Peter's lab", xaxis_title="Date",yaxis_title="Humidity (%)")

      fig_press = go.Figure()
      fig_press.add_trace(go.Scatter(x=time_series_adjusted_pressure,y=time_series_pressure_values,name="Pressure",line=dict(color='firebrick', width=4)))
      fig_press.update_layout(title="Humidity in Peter's lab", xaxis_title="Date",yaxis_title="Pressure (hPa)")

      plot_url_temp = "static/temperature.html"
      plot_url_hum = "static/humidity.html"
      plot_url_press = "static/pressure.html"
      base_url = "/var/www/lab_app/" # The base url defines the absolute path for the application.
      fig_temp.write_html(base_url + plot_url_temp, auto_open=False)
      fig_hum.write_html(base_url + plot_url_hum, auto_open=False)
      fig_press.write_html(base_url + plot_url_press, auto_open=False)

      print("plot_url:","/" +  plot_url_temp)
      return_dictionary = {
                "temp_url": "/" + plot_url_temp,
                "hum_url": "/" + plot_url_hum,
                "press_url": "/" + plot_url_press
              }
      return return_dictionary

def get_last_record(sensor_id):
    ''' Get the last temperature and humidity readings from the database over the last hour for sensor_id'''

    # Get datetime objects for now and one hour ago
    to_date_utc = datetime.datetime.now()
    to_date_str = to_date_utc.strftime('%Y-%m-%d %H:%M')

    # Convert to strings needed for SQL query
    from_date_utc = to_date_utc - datetime.timedelta(hours = 1)
    from_date_str = from_date_utc.strftime('%Y-%m-%d %H:%M')

    # Connect to the SQL database
    conn = sqlite3.connect('/var/www/lab_app/lab_app.db')
    curs = conn.cursor()

    # Get temperature and humidity readings over the last hour
    temp_sql = f"SELECT * FROM temperatures WHERE (rDateTime BETWEEN '{from_date_str}' AND '{to_date_str}') AND sensorID = {sensor_id}"
    curs.execute(temp_sql)
    temperatures = curs.fetchall()
    print(temperatures)

    hum_sql = f"SELECT * FROM humidities WHERE (rDateTime BETWEEN '{from_date_str}' AND '{to_date_str}') AND sensorID = {sensor_id}"

    curs.execute(hum_sql)
    humidities = curs.fetchall()
    print(humidities)

    current_temp = None
    current_hum = None

    if len(temperatures) and len(humidities):
        try:
            # Get the last record in the list for this sensor ID
            _,_,current_temp = temperatures[-1]
            _,_,current_hum = humidities[-1]
        except:
            print('Could not parse either temperature or humidity record from DB')

    if current_temp is not None and current_hum is not None:
        print(f'temp: {current_temp}, hum: {current_hum}')
    else:
        print(f'No records available for sensor ID {sensor_id}')

    # Close the SQL database and return current readings.
    conn.close()
    return (current_temp, current_hum)


def validate_date(d):
    try:
        datetime.strptime(d, '%Y-%m-%d %H:%M')
        return True
    except ValueError:
        return False

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
