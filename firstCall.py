import os
from twilio.rest import Client
import time
from datetime import datetime, timezone, timedelta
import csv
import pyodbc
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

server = os.environ.get("serverGFT")
database = os.environ.get("databaseGFT")
username = os.environ.get("usernameGFT")
password = os.environ.get("passwordGFT")
SQLaddress = os.environ.get("addressGFT")


def assignCall(account_sid, auth_token, assignQuestion, tech_phone_number,twilio_number):
    print("Processing: ", assignQuestion)
    time.sleep(1)  
    client = Client(account_sid, auth_token)
    call_timestamps = []
    # message method
    message_timestamp = datetime.now(timezone.utc)
    message = client.messages.create(
        body=assignQuestion,
        from_=twilio_number,
        to=tech_phone_number
    )
    while True:
        # check every 10 sec
        time.sleep(10)

        response = client.messages.list(
            from_=tech_phone_number,
            to=twilio_number,
            limit=1
        )
        message_timestamp_str = message_timestamp.strftime("%Y-%m-%d%H:%M")
        print(response[0].body, datetime.now(timezone.utc) - message_timestamp, message_timestamp_str)
        if datetime.now(timezone.utc) - message_timestamp > timedelta(minutes=15):
            print(call_timestamps)
            if len(call_timestamps) != 0 and datetime.now(timezone.utc) - call_timestamps[0] > timedelta(minutes=25):
                print("call service manager")
                # call_timestamps.append(datetime.now(timezone.utc))
                # call = client.calls.create(
                #     to=tech_phone_number,
                #     from_="+18556258756",
                #     url=f"https://handler.twilio.com/twiml/EHde6244b9fd963fe81b6c0fc467d07740?Name=Charlie&Date={message_timestamp_str}"
                # )
                # print("Initiating a phone call to remind the tech to acknowledge the call.")
            if len(call_timestamps) == 0 or datetime.now(timezone.utc) - call_timestamps[-1] > timedelta(minutes=10):
                call_timestamps.append(datetime.now(timezone.utc))
                call = client.calls.create(
                    to=tech_phone_number,
                    from_="+18556258756",
                    url=f"https://handler.twilio.com/twiml/EHde6244b9fd963fe81b6c0fc467d07740?Name=Charlie&Date={message_timestamp_str}"
                )
                print("Initiating a phone call to remind the tech to acknowledge the call.")
        if response:
            latest_response = response[0]
            if (
                latest_response.body.lower() in ['1', 'yes', 'y']
                and latest_response.date_sent > message_timestamp
            ):
                print("Tech accepted the call.")
                return 1, message_timestamp, latest_response.date_sent
                break 
            elif (
                latest_response.body.lower() in ['2', 'no', 'n']
                and latest_response.date_sent > message_timestamp
            ):
                print("Tech declined the call.")
                return 0, message_timestamp, latest_response.date_sent
                break

# def assignCall(account_sid, auth_token, assignQuestion, tech_phone_number, twilio_number):
#     print("Processing: ", assignQuestion)
#     time.sleep(1)  

def process_row(row):
    account_sid = row['account_sid']
    auth_token = row['auth_token']
    assignQuestion = row['assignMessage']
    tech_phone_number = row['tech_phone_number']
    twilio_number = row['twilio_number']
    temp = assignCall(account_sid, auth_token, assignQuestion, tech_phone_number, twilio_number)
    return temp

if __name__ == "__main__":
    with open("assignCall.csv", 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)

        with ThreadPoolExecutor(max_workers=10) as executor: 
            futures = [executor.submit(process_row, row) for row in csv_reader]

            for future in futures:
                try:
                    result_row = future.result()
                    print("Thread execution succeeded:", result_row)
                except Exception as e:
                    print(f"Thread execution failed: {e}")