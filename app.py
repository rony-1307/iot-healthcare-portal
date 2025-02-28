# Insert Header File ==========
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import base64, json, os, sqlite3, serial, time, mysql.connector
from scipy.stats import entropy
import matplotlib.pyplot as plt
import io
import base64
import numpy as np
import matplotlib
matplotlib.use('Agg')
from datetime import datetime

from flask import render_template
import matplotlib.pyplot as plt
import io
import base64
import numpy as np
from matplotlib.ticker import MaxNLocator, MultipleLocator

# Configure the serial port ==========
SERIAL_PORT = "COM6"
BAUD_RATE = 115200
ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
time.sleep(0)
ecgData = []
bpData = []

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database configuration ==========
def iot_health_database():
  connection = mysql.connector.connect(
    host = "localhost",
    user = "root",
    password = "",
    database = "iot_health_db"
    )
  return connection

# Function to calculate age
def calculate_age(dob):
    today = datetime.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))  # Adjust if birthday hasn't happened yet this year
    return age

# Insert process data to the database
def insert_data(ecgData, bpData, patientId, patientWeight, testDate, testTime, doctorName):
    connection = iot_health_database()
    cursor = connection.cursor()

    # Safely constructing the query without interpolating the table name directly
    query = f'''
        INSERT INTO `{patientId}` (testDate, testTime, doctorName, patientWeight, ecgData, bpData)
        VALUES (%s, %s, %s, %s, %s, %s)
    '''
    
    # Execute the query with parameters
    cursor.execute(query, (testDate, testTime, doctorName, patientWeight, ecgData, bpData))
    
    connection.commit()
    cursor.close()
    connection.close()
    
    return "Data inserted successfully into the database"


# Route Code ==========
# INDEX Page ==========
@app.route('/')
def index():
  return render_template('index.html')


# PATIENT REGISTRATION FORM Page ==========
@app.route('/patientRegistration')
def patientRegistration():
  return render_template('form_patientRegistration.html')

# ADD NEW PATINET Action ==========
@app.route('/patientRegistration/addNewPatient', methods=['POST'])
def addNewPatient():
  if request.method == 'POST':
    name = request.form['name']
    gender = request.form['gender']
    dob = request.form['dob']
    phoneNo = request.form['phoneNo']
    emailId = request.form['emailId']
    address = request.form['address']
    pId = request.form['pId']
    try:
      conn = iot_health_database()
      cursor = conn.cursor()

      cursor.execute("""
                     INSERT INTO `patient_db` (name, gender, dob, phoneNo, emailId, address, pId)
                     VALUES (%s, %s, %s, %s, %s, %s, %s)
                     """, (name, gender, dob, phoneNo, emailId, address, pId))
      conn.commit()
      create_table_query = f"""
      CREATE TABLE IF NOT EXISTS `{pId}` (
      `slNo` int(3) NOT NULL AUTO_INCREMENT,
      `testDate` date NOT NULL DEFAULT current_timestamp(),
      `testTime` time NOT NULL DEFAULT current_timestamp(),
      `doctorName` varchar(60) NOT NULL,
      `patientWeight` float NOT NULL,
      `ecgData` text NOT NULL,
      `bpData` text NOT NULL,
      PRIMARY KEY (`slNo`)
      ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci;
      """

      cursor.execute(create_table_query)
      conn.commit()
      cursor.close()
      conn.close()
      return "Patient Registered Successfully and Record Table Created!"
    except mysql.connector.Error as err:
      return f"Error: {err}"
    
# VIEW OLD REPORT RECORD Page ==========
@app.route('/patientReportsRecord', methods=['GET','POST'])
def patientReportsRecord():
  patientDetials = None
  patientReportsRecord = None
  age = None
  try:
    if request.method == 'POST':
      print(request.method)
      conn = iot_health_database()
      cursor = conn.cursor(dictionary=True)
      patientId = request.form['patient_id']
      cursor.execute("SELECT * FROM `patient_db` WHERE pId = %s", (patientId,))
      patientDetials = cursor.fetchone()

      age = calculate_age(patientDetials['dob'])
      
      cursor.execute(f"SELECT * FROM {patientId}")
      patientReportsRecord = cursor.fetchall()
      cursor.close()
      conn.close()
  except mysql.connector.Error as err:
    return f"Error: {err}"
  return render_template('patientReportsRecord.html', patientDetials=patientDetials, patientReportsRecord=patientReportsRecord, age=age)

@app.route('/patientReportAnalysis/<string:pId>/<int:id>', methods=['GET'])
def view_report(pId, id):
    # Use context manager for database connection
    with iot_health_database() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM `patient_db` WHERE pId = %s", (pId,))
            patientDetails = cursor.fetchone()

            # Calculate age
            age = calculate_age(patientDetails['dob'])

            cursor.execute(f"SELECT * FROM `{pId}` WHERE slNo = %s", (id,))
            patientReport = cursor.fetchone()

            print(patientReport['ecgData'])  # Debugging line

            # Handle ECG data: validate and process
            if patientReport['ecgData']:
                try:
                    ecg_data = list(map(int, patientReport['ecgData'].split(',')))
                    if not ecg_data:
                        ecg_data = [0]
                except ValueError:
                    ecg_data = [0]
            else:
                ecg_data = [0]

            # Handle BP data: validate and process
            if patientReport['bpData']:
                try:
                    bp_data = list(map(int, patientReport['bpData'].split(',')))
                    if not bp_data:
                        bp_data = [0]
                except ValueError:
                    bp_data = [0]
            else:
                bp_data = [0]

            # Debugging: Log the data being used for plotting
            print(f"ECG Data: {ecg_data}")
            print(f"BP Data: {bp_data}")

            # Vary the sample length (e.g., display every nth sample from ECG data)
            sample_length = 400  # Adjust to control the number of points displayed
            if len(ecg_data) > sample_length:
                ecg_data = ecg_data[:sample_length]

            # Create ECG plot with grid
            fig, ax = plt.subplots(figsize=(30, 3))

            # Plot the ECG data with a thicker line
            ax.plot(ecg_data, marker='', linestyle='-', color='black', label='ECG Data', linewidth=1)

            # Customize labels and add grid
            ax.set_xlabel('Time')
            ax.set_ylabel('Amplitude')
            ax.legend()

            # Increase gridline density
            ax.grid(True, which='both', color='green', linestyle='-', linewidth=0.5)
            ax.grid(True, which='minor', color='blue', linestyle='--', linewidth=0.2)  # Additional minor grid lines

            # Use MaxNLocator to adjust major and minor gridline spacing
            #ax.xaxis.set_major_locator(MaxNLocator(integer=True, prune='lower'))  # Set major ticks
            #ax.yaxis.set_major_locator(MaxNLocator(integer=True, prune='lower'))  # Set major ticks
            
            # Use MaxNLocator to adjust major and minor gridline spacing
            ax.xaxis.set_major_locator(MultipleLocator(5))  # Major gridlines every 20 samples
            ax.yaxis.set_major_locator(MultipleLocator(150))  # Major gridlines every 50 units on the y-axis

            # Optional: Add minor gridlines for finer granularity
            #ax.minorticks_on()
            #ax.xaxis.set_minor_locator(MaxNLocator(integer=True, prune='both'))
            #ax.yaxis.set_minor_locator(MaxNLocator(integer=True, prune='both'))

            # Optional: Add minor gridlines for finer granularity
            ax.minorticks_on()  # Enable minor ticks
            ax.xaxis.set_minor_locator(MultipleLocator(10))  # Minor gridlines every 5 samples
            ax.yaxis.set_minor_locator(MultipleLocator(10))  # Minor gridlines every 10 units on the y-axis

            # Set axis limits to start from (0, 0)
            ax.set_xlim(left=0, right=len(ecg_data))  # Start x-axis from 0
            ax.set_ylim(bottom=0, top=max(ecg_data))  # Start y-axis from 0

            # Incline the x-axis tick labels by 45 degrees
            plt.xticks(rotation=60)

            # Incline the x-axis tick labels by 45 degrees
            plt.xticks(rotation=45)

            # Save the plot to a BytesIO object
            ecg_img = io.BytesIO()
            plt.savefig(ecg_img, format='png', dpi=1200)  # Use a more reasonable DPI for web
            ecg_img.seek(0)
            ecg_img_base64 = base64.b64encode(ecg_img.getvalue()).decode('utf-8')
            plt.close()

            # Pass BP values directly (assuming bp_data can be used as is)
            bp_value = bp_data  # You might want to show the first value or process further

    # Return the rendered HTML template
    return render_template('viewReport.html', patientDetails=patientDetails, patientReport=patientReport, ecg_img_base64=ecg_img_base64, bp_value=bp_value, age=age)

@app.route('/takeNewReport', methods=['GET','POST'])
def takeNewReport():
    patient_details = None
    patient_report = None
    age = None
    try:
      if request.method == 'POST':
        conn = iot_health_database()
        cursor = conn.cursor(dictionary=True)
        patient_id = request.form['patient_id']
        cursor.execute("SELECT * FROM `patient_db` WHERE pId = %s", (patient_id,))
        patient_details = cursor.fetchone()
        age = calculate_age(patient_details['dob'])
        cursor.execute(f"SELECT * FROM {patient_id}")
        patient_report = cursor.fetchall()
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
      return f"Error: {err}"
    return render_template('takeNewReport.html', patient_details=patient_details, patient_report = patient_report, age=age)

@app.route('/data/<string:patientId>/<float:patientWeight>/<string:testDate>/<string:testTime>/<string:doctorName>')
#@app.route('/data/<string:patientId>/<string:testDate>/<string:testTime>/<string:doctorName>')
def data(patientId, patientWeight, testDate, testTime, doctorName):
    # Initialize variables in case there's no data from serial port
    ecg_data = None
    bp_data = None
    bp_received = False  # Default to False if no data is received
    
    # Only read from the serial port if it is open
    if ser.is_open and ser.in_waiting > 0:
        try:
            line = ser.readline().decode('utf-8').rstrip()
            #print(line) # modification

            # Check if the line contains comma-separated values (BP data)
            if ',' in line:
                bp_data = line.split(',')
                bpData.extend(bp_data)
                bp_data = [int(x) for x in bp_data]  # Convert BP data to integers
                ecg_data = None  # No ECG data for this line
                bp_received = True  # Flag indicating BP data received
                ecgData_str = ','.join(ecgData)
                bpData_str = ','.join(bpData)
                print('ecgData_str:', ecgData_str)
                insert_data(ecgData_str, bpData_str, patientId, patientWeight, testDate, testTime, doctorName)
            else:
                ecg_data = int(line)  # Convert ECG data to integer
                print('ecgData:', ecgData)
                bp_data = None  # No BP data for this line
                bp_received = False
                ecgData.append(line)

            #print(f"ECG Data: {ecg_data}")  # Print ECG data to terminal
            #print(f"BP Data: {bp_data}")    # Print BP data to terminal

        except serial.SerialException as e:
            print(f"Error reading from serial: {e}")

    # Return the response with the proper values
    return jsonify(ecg=ecg_data, bp=bp_data, bp_received=bp_received)

# Run App.py on mantioned ip ==========
if __name__ == "__main__":
  app.run(host='0.0.0.0', port=5000)
  #app.run(debug=True)