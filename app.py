# Import necessary libraries ==========
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from matplotlib import pyplot as plt
import mysql
import base64, json, os, serial, time
from datetime import datetime
from matplotlib.ticker import MaxNLocator, MultipleLocator
import sys
import subprocess
import io
import numpy as np
import matplotlib
import pymongo
from pymongo import MongoClient
matplotlib.use('Agg')
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, BulkWriteError

# Flask App Connection ==========
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Function to connect to MongoDB Local Database
def iot_health_database_local():
    cluster_uri = "mongodb://localhost:27017/"
    database_name = "iot_health_db"
    client = MongoClient(cluster_uri)
    db = client[database_name]
    return db

# Function to connect to MongoDB Online Database
def iot_health_database_online():
    cluster_uri = "mongodb+srv://root:root@cluster0.qgczj.mongodb.net/"
    database_name = "iot_health_db"
    client = MongoClient(cluster_uri)
    db = client[database_name]
    return db

# Function to calculate age
def calculate_age(dob):
    if isinstance(dob, str):  # Check if dob is a string
        dob = datetime.strptime(dob, "%Y-%m-%d")  # Convert string to datetime object
    today = datetime.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))  # Adjust if birthday hasn't happened yet this year
    return age

# Route Code ==========

# INDEX Page ==========
@app.route('/')
def index():
  return render_template('index.html')

# VIEW ALL ENLISTED PATINET Page ==========
@app.route('/viewEnlistedPatient')
def viewEnlistedPatient():
    db = iot_health_database_online()
    collection = db['patient_db']
    patients_list = list(collection.find())  # Get all patients from the database
    #age = calculate_age(patients_list['dob'])
    return render_template('viewEnlistedPatient.html', patients=patients_list)

# VIEW INDIVISUAL REPORT RECORD Page ==========
@app.route('/patientReportsRecord/<string:pId>')
def indivisualReportRecord(pId):
    patientDetials = None
    patientReportsRecord = None
    age = None

    db = iot_health_database_online()
    collection = db['patient_db']
    patientId = pId
    patientDetials = collection.find_one({"pId": patientId})
    if patientDetials:
          age = calculate_age(patientDetials['dob'])

          # Assuming test records for the patient are in a subcollection or embedded in the patient document
          patientReportsRecord = patientDetials.get("reports", [])
    else:
          return "Patient not found in the database"
    
    return render_template('patientIndivisualRecord.html', patientDetials=patientDetials, patientReportsRecord=patientReportsRecord, age=age)

# VIEW OLD REPORT RECORD Page ==========
@app.route('/patientReportsRecord', methods=['GET','POST'])
def patientReportsRecord():
  patientDetials = None
  patientReportsRecord = None
  age = None
  try:
    if request.method == 'POST':
      db = iot_health_database_online()
      collection = db['patient_db']
      patientId = request.form['patient_id']
      patientDetials = collection.find_one({"pId": patientId})

      if patientDetials:
          age = calculate_age(patientDetials['dob'])

          # Assuming test records for the patient are in a subcollection or embedded in the patient document
          patientReportsRecord = patientDetials.get("reports", [])
      else:
          return "Patient not found in the database"

  except pymongo.errors.PyMongoError as err:
    return f"Error: {err}"
  return render_template('patientReportsRecord.html', patientDetials=patientDetials, patientReportsRecord=patientReportsRecord, age=age)

# PATIENT REPORT ANALYSIS Page ==========
@app.route('/patientReportAnalysis/<string:pId>/<int:id>', methods=['GET'])
def view_report(pId, id):
    # Use context manager for MongoDB connection
    db = iot_health_database_online()
    collection = db['patient_db']

    patientDetails = collection.find_one({"pId": pId})

    if not patientDetails:
        return "Patient not found!"

    # Calculate age
    age = calculate_age(patientDetails['dob'])

    patientReport = next((report for report in patientDetails['reports'] if report['slNo'] == id), None)

    if not patientReport:
        return "Report not found!"

    # Process ECG data
    if patientReport['ecgData']:
        try:
            ecg_data = list(map(int, patientReport['ecgData'].split(',')))
            if not ecg_data:
                ecg_data = [0]
        except ValueError:
            ecg_data = [0]
    else:
        ecg_data = [0]

    # Process BP data
    if patientReport['bpData']:
        try:
            bp_data = list(map(int, patientReport['bpData'].split(',')))
            if not bp_data:
                bp_data = [0]
        except ValueError:
            bp_data = [0]
    else:
        bp_data = [0]

    # Vary the sample length (e.g., display every nth sample from ECG data)
    sample_length = 400
    if len(ecg_data) > sample_length:
        ecg_data = ecg_data[:sample_length]

    # Create ECG plot with grid
    fig, ax = plt.subplots(figsize=(30, 3))
    ax.plot(ecg_data, marker='', linestyle='-', color='black', label='ECG Data', linewidth=1)
    ax.set_xlabel('Time')
    ax.set_ylabel('Amplitude')
    ax.legend()
    ax.grid(True, which='both', color='green', linestyle='-', linewidth=0.5)
    ax.grid(True, which='minor', color='blue', linestyle='--', linewidth=0.2)
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.yaxis.set_major_locator(MultipleLocator(150))
    ax.minorticks_on()
    ax.xaxis.set_minor_locator(MultipleLocator(10))
    ax.yaxis.set_minor_locator(MultipleLocator(10))
    ax.set_xlim(left=0, right=len(ecg_data))
    ax.set_ylim(bottom=0, top=max(ecg_data))
    plt.xticks(rotation=45)

    # Save the plot to a BytesIO object
    ecg_img = io.BytesIO()
    plt.savefig(ecg_img, format='png', dpi=200)
    ecg_img.seek(0)
    ecg_img_base64 = base64.b64encode(ecg_img.getvalue()).decode('utf-8')
    plt.close()

    # Return the rendered HTML template
    return render_template('viewReport.html', patientDetails=patientDetails, patientReport=patientReport, ecg_img_base64=ecg_img_base64, bp_value=bp_data, age=age)

# RUN App.py on MENTIONED IP ==========
if __name__ == "__main__":
  app.run(host='0.0.0.0', port=5000)
