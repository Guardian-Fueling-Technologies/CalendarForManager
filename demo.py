from streamlit_calendar import calendar
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import time
import pyodbc
import subprocess
import threading
import re
import csv
import os

server = os.environ.get("serverGFT")
database = os.environ.get("databaseGFT")
username = os.environ.get("usernameGFT")
password = os.environ.get("passwordGFT")
SQLaddress = os.environ.get("addressGFT")
account_sid = os.environ.get("account_sid")
auth_token = os.environ.get("auth_token")

def createCsv():
    conn_str = f"DRIVER={SQLaddress};SERVER={server};DATABASE={database};UID={username};PWD={password};"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    sql_query = '''
        SELECT [Name]
      ,[Color]
      ,CAST([Start] AS NVARCHAR(MAX)) AS StartString
      ,CAST([End] AS NVARCHAR(MAX)) AS EndString
      ,[Technician_ID]
      ,[ResourceId]
      ,[Region]
      ,[BranchName]
      ,[Email]
      ,CAST([ManagerPhone] AS NVARCHAR(MAX)) AS ManagerPhone
        FROM [GFT].[dbo].[CF_OnCall_Calendar_Events]
        '''    
    # WHERE [Start] > ?
    # cursor.execute(sql_query, today)
    # result = cursor.fetchall()
    
    cursor.execute(sql_query)
    result = cursor.fetchall()
    data = [list(row) for row in result]
    eventDf = pd.DataFrame(data, columns=['Name', 'Color', 'Start', 'End', 'Technician_ID', 'ResourceId', 'Region', 'BranchName', 'Email', 'ManagerPhone'])

    sql_query = '''
        SELECT [BranchName]
        ,[Name]
        ,[Phone]
        ,[Email]
        ,[Team]
        ,CAST([RowID] AS NVARCHAR(MAX)) AS RowIDString
        FROM [GFT].[dbo].[CF_OnCall_Contact]
        WHERE [Phone] <> '0000000000'
        '''    
    cursor.execute(sql_query)
    result = cursor.fetchall()
    data = [list(row) for row in result]
    contactDf = pd.DataFrame(data, columns=['BranchName', 'Name', 'Phone', 'Email', 'Team', 'RowID'])

    cursor.close()
    conn.close()

    if(len(contactDf)!=0):
        merged_df = pd.merge(contactDf, eventDf, on="Email", how="inner", suffixes=('_contact', '_event'))
        # merged_df = pd.merge(contactDf, eventDf, on="Email", how="inner")

        with open("assignCall.csv", mode='w', newline='') as file:
            fieldnames = ["account_sid", "auth_token", "assignMessage", "tech_phone_number", "twilio_number", "assigned", "technician_manager_phone"]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

        with open("assignCall.csv", mode='a', newline='') as file:
            fieldnames = ["account_sid", "auth_token", "assignMessage", "tech_phone_number", "twilio_number", "assigned","technician_manager_phone"]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            for index, row in merged_df.iterrows():
                writer.writerow({
                "account_sid": account_sid, 
                "auth_token": auth_token,
                    "assignMessage": f"Are you ready to accept this call from {row['Start'][:19]} to {row['End'][:19]}, {row['Name_contact']}? ",
                    "tech_phone_number": f"1{row['Phone']}",
                    "twilio_number": 18556258756,
                    "assigned": 0,
                    "technician_manager_phone":f"1{row['ManagerPhone']}"
                })
    return

def run_assignCall_app():
    try:
        result = subprocess.run(['python', '../../twillioassigncall/firstCall.py'], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return e.stderr

def getAll():
    conn_str = f"DRIVER={SQLaddress};SERVER={server};DATABASE={database};UID={username};PWD={password};"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    sql_query = '''
        SELECT DISTINCT RTrim(Wennsoft_Branch) as Wennsoft_Branch , Rtrim(BranchName) as BranchName FROM [dbo].[GFT_SV00077_Ext]
        WHERE Wennsoft_Branch <> 'Pensacola' AND BranchName NOT IN ('Pensacola', 'Corporate', 'Guardian Connect')
        '''    
    cursor.execute(sql_query)
    result = cursor.fetchall()
    rows_transposed = [result for result in zip(*result)]
    branchDf = pd.DataFrame(dict(zip(['Wennsoft_Branch', 'BranchName'], rows_transposed)))
    
    sql_query = '''
        SELECT [Name]
      ,[Color]
      ,CAST([Start] AS NVARCHAR(MAX)) AS StartString
      ,CAST([End] AS NVARCHAR(MAX)) AS EndString
      ,[Technician_ID]
      ,[ResourceId]
      ,[Region]
      ,[BranchName]
      ,[Email]
      ,CAST([ManagerPhone] AS NVARCHAR(MAX)) AS ManagerPhone
      ,CAST([RowID] AS NVARCHAR(MAX)) AS RowIDString
        FROM [GFT].[dbo].[CF_OnCall_Calendar_Events]
        '''    
    cursor.execute(sql_query)
    result = cursor.fetchall()
    data = [list(row) for row in result]
    eventDf = pd.DataFrame(data, columns=['Name', 'Color', 'Start', 'End', 'Technician_ID', 'ResourceId', 'Region', 'BranchName', 'Email', 'ManagerPhone',"RowID"])

    sql_query = '''
        SELECT [BranchName]
      ,[Name]
      ,[Phone]
      ,[Email]
      ,[Team]
      ,CAST([RowID] AS NVARCHAR(MAX)) AS RowIDString
    FROM [GFT].[dbo].[CF_OnCall_Contact]
        '''    
    cursor.execute(sql_query)
    result = cursor.fetchall()
    data = [list(row) for row in result]
    contactDf = pd.DataFrame(data, columns=['BranchName', 'Name', 'Phone', 'Email', 'Team',"RowID"])

    conn_str = f"DRIVER={SQLaddress};SERVER={server};DATABASE={database};UID={username};PWD={password};"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    sql_query = '''
        Exec CF_P_TechID
        '''    
    cursor.execute(sql_query)
    result = cursor.fetchall()
    data = [list(row) for row in result]
    columns = [column[0] for column in cursor.description]
    IdDf = pd.DataFrame(data, columns=columns)

    cursor.close()
    conn.close()
    return branchDf, contactDf, eventDf, IdDf

def updateEvents(eventDf):
    conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    df_columns = ['Name', 'Color', 'Start', 'End', 'Technician_ID', 'ResourceId', 'Region', 'BranchName', 'Email', 'ManagerPhone']

    for row_id, row in eventDf.iterrows():
        if(row_id[1]=='self'):
            continue
        update_query = f'UPDATE [GFT].[dbo].[CF_OnCall_Calendar_Events] SET '
        values = []
        for col in df_columns:
            if col in row.index:
                update_query += f'[{col}] = ?, '
                values.append(row[col])

        update_query = update_query.rstrip(', ')
        update_query += ' WHERE [RowID] = ?'
        values.append(row_id[0])
        # print(update_query, values)
        cursor.execute(update_query, values)
        conn.commit()

    sql_query = '''
        SELECT [Name]
            ,[Color]
            ,[Start]
            ,[End]
            ,[Technician_ID]
            ,[ResourceId]
            ,[Region]
            ,[BranchName]
            ,[Email]
            ,[ManagerPhone]
            ,[RowID]
        FROM [GFT].[dbo].[CF_OnCall_Calendar_Events]
    '''
    cursor.execute(sql_query)
    sql_query = cursor.fetchall()
    rows_transposed = [sql_query for sql_query in zip(*sql_query)]
    updatedEvent = pd.DataFrame(dict(zip(['Name', 'Color', 'Start', 'End', 'Technician_ID', 'ResourceId', 'Region', 'BranchName'
      ,'Email', 'ManagerPhone', 'RowID'], rows_transposed)))
    
    cursor.close()
    conn.close()
    return updatedEvent
    
def deleteEvents(eventDf):
    conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    delete_query = "DELETE FROM [GFT].[dbo].[CF_OnCall_Calendar_Events] WHERE RowID = ?"
    
    for index, row in eventDf.iterrows():
        row_id = row["RowID"]
        cursor.execute(delete_query, (row_id,))
        conn.commit()
    
    sql_query = '''
        SELECT [Name]
            ,[Color]
            ,[Start]
            ,[End]
            ,[Technician_ID]
            ,[ResourceId]
            ,[Region]
            ,[BranchName]
            ,[Email]
            ,[ManagerPhone]
            ,[RowID]
        FROM [GFT].[dbo].[CF_OnCall_Calendar_Events]
    '''
    cursor.execute(sql_query)
    sql_query = cursor.fetchall()
    rows_transposed = [sql_query for sql_query in zip(*sql_query)]
    updatedEvent = pd.DataFrame(dict(zip(['Name', 'Color', 'Start', 'End', 'Technician_ID', 'ResourceId', 'Region', 'BranchName'
      ,'Email', 'ManagerPhone', 'RowID'], rows_transposed)))
    
    cursor.close()
    conn.close()
    return updatedEvent

def insertEvents(eventDf):
    conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    data = eventDf[['Name', 'Color', 'Start', 'End', 'Technician_ID', 'ResourceId', 'Region', 'BranchName','Email','ManagerPhone']].values.tolist()
    data = [row for row in data]
    insert_query = "INSERT INTO [GFT].[dbo].[CF_OnCall_Calendar_Events] ([Name], [Color], [Start], [End], [Technician_ID], [ResourceId], [Region], [BranchName], [Email], [ManagerPhone]) VALUES (?,?,?,?,?,?,?,?,?)"
    if data:
        cursor.executemany(insert_query, data)
        conn.commit()

    sql_query = '''
        SELECT [Name]
            ,[Color]
            ,[Start]
            ,[End]
            ,[Technician_ID]
            ,[ResourceId]
            ,[Region]
            ,[BranchName]
            ,[Email]
            ,[ManagerPhone]
            ,[RowID]
        FROM [GFT].[dbo].[CF_OnCall_Calendar_Events]
    '''
    cursor.execute(sql_query)
    sql_query = cursor.fetchall()
    rows_transposed = [sql_query for sql_query in zip(*sql_query)]
    updatedEvent = pd.DataFrame(dict(zip(['Name', 'Color', 'Start', 'End', 'Technician_ID','ResourceId', 'Region', 'BranchName'
      ,'Email', 'ManagerPhone', 'RowID'], rows_transposed)))
    
    cursor.close()
    conn.close()
    return updatedEvent

def updateContact(contactDF):
    conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    df_columns = ['BranchName', 'Name', 'Phone', 'Email', 'Team']

    for row_id, row in contactDF.iterrows():
        if(row_id[1]=='self'):
            continue
        update_query = f'UPDATE [GFT].[dbo].[CF_OnCall_Contact] SET '
        values = []
        for col in df_columns:
            if col in row.index:
                update_query += f'[{col}] = ?, '
                values.append(row[col])

        update_query = update_query.rstrip(', ')
        update_query += ' WHERE [RowID] = ?'
        values.append(row_id[0])
        # print(update_query, values)
        cursor.execute(update_query, values)
        conn.commit()

        sql_query = '''
            SELECT [BranchName]
                ,[Name]
                ,[Phone]
                ,[Email]
                ,[Team]
                ,[RowID]
            FROM [GFT].[dbo].[CF_OnCall_Contact]
        '''
        cursor.execute(sql_query)
        sql_query = cursor.fetchall()
        rows_transposed = [sql_query for sql_query in zip(*sql_query)]
        updatedEvent = pd.DataFrame(dict(zip(['BranchName', 'Name', 'Phone', 'Email', 'Team', 'RowID'], rows_transposed)))
        
        cursor.close()
        conn.close()
        return updatedEvent

def deleteContact(contactDf):
    conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    delete_query = "DELETE FROM [GFT].[dbo].[CF_OnCall_Contact] WHERE RowID = ?"
    
    for index, row in contactDf.iterrows():
        row_id = row["RowID"]
        cursor.execute(delete_query, (row_id,))
        conn.commit()
    
    sql_query = '''
        SELECT [BranchName]
            ,[Name]
            ,[Phone]
            ,[Email]
            ,[Team]
            ,[RowID]
        FROM [GFT].[dbo].[CF_OnCall_Contact]
    '''
    cursor.execute(sql_query)
    sql_query = cursor.fetchall()
    rows_transposed = [sql_query for sql_query in zip(*sql_query)]
    updatedEvent = pd.DataFrame(dict(zip(['BranchName', 'Name', 'Phone', 'Email', 'Team', 'RowID'], rows_transposed)))
    
    cursor.close()
    conn.close()
    return updatedEvent

def insertContact(contactDF):
    conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    data = contactDF[['BranchName', 'Name', 'Phone', 'Email', 'Team']].values.tolist()
    data = [row for row in data]
    insert_query = "INSERT INTO [GFT].[dbo].[CF_OnCall_Contact] ([BranchName], [Name], [Phone], [Email], [Team]) VALUES (?,?,?,?,?)"
    if data:
        cursor.executemany(insert_query, data)
        conn.commit()

    sql_query = '''
        SELECT [BranchName]
            ,[Name]
            ,[Phone]
            ,[Email]
            ,[Team]
            ,[RowID]
        FROM [GFT].[dbo].[CF_OnCall_Contact]
    '''
    cursor.execute(sql_query)
    sql_query = cursor.fetchall()
    rows_transposed = [sql_query for sql_query in zip(*sql_query)]
    updatedEvent = pd.DataFrame(dict(zip(['BranchName', 'Name', 'Phone', 'Email', 'Team', 'RowID'], rows_transposed)))
    
    cursor.close()
    conn.close()
    return updatedEvent

st.set_page_config(page_title="On Call Schedule Calendar", page_icon="📆", layout="wide")

calendar_options = {}
if "branch" not in st.session_state:
    st.session_state.branch, st.session_state.contacts, st.session_state.calendar_events, st.session_state.IdDf = getAll()
# if "contacts" not in st.session_state:
#     st.session_state.branch, st.session_state.contacts, st.session_state.calendar_events = getAll()
# if "calendar_events" not in st.session_state:
#     st.session_state.branch, st.session_state.contacts, st.session_state.calendar_events = getAll()
# st.write(st.session_state.branch)
# st.write(st.session_state.contacts)
# st.write(st.session_state.calendar_events)
if 'changed' not in st.session_state:
    st.session_state.changed = False
if 'selected_branches' not in st.session_state:
    st.session_state.selected_branches = ['Atlanta']
if 'filtered_events' not in st.session_state:
    mask = st.session_state.calendar_events['BranchName'].isin(st.session_state.selected_branches)
    st.session_state.filtered_events = st.session_state.calendar_events[mask]
if 'filtered_contacts' not in st.session_state:
    mask = st.session_state.contacts['BranchName'].isin(st.session_state.selected_branches)
    st.session_state.filtered_contacts = st.session_state.contacts[mask]
if 'filtered_IDs' not in st.session_state:
    mask = st.session_state.IdDf['BranchName'].isin(st.session_state.selected_branches)
    st.session_state.filtered_IDs = st.session_state.IdDf[mask]

if 'deleterowEvent' not in st.session_state:
    st.session_state.deleterowEvent = pd.DataFrame()
if 'insertrowEvent' not in st.session_state:
    st.session_state.insertrowEvent = pd.DataFrame()
if 'updaterowEvent' not in st.session_state:
    st.session_state.updaterowEvent = pd.DataFrame()
if 'deleterowContact' not in st.session_state:
    st.session_state.deleterowContact = pd.DataFrame()
if 'insertrowContact' not in st.session_state:
    st.session_state.insertrowContact = pd.DataFrame()
if 'updaterowContact' not in st.session_state:
    st.session_state.updaterowContact = pd.DataFrame()
if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = "Calendar"

st.sidebar.subheader("BranchName")
# branch_names_set = set(event['BranchName'] for event in st.session_state.calendar_events)
selected_branches = st.sidebar.multiselect("Select Branches", st.session_state.branch['BranchName'], key="select_branches")
if selected_branches != None and selected_branches != st.session_state.selected_branches:
    st.session_state.selected_branches = selected_branches
    mask = st.session_state.calendar_events['BranchName'].isin(st.session_state.selected_branches)    
    st.session_state.filtered_events = pd.DataFrame(columns=st.session_state.calendar_events.columns)
    st.session_state.filtered_events = pd.concat(
    [st.session_state.filtered_events, st.session_state.calendar_events[mask]],
    ignore_index=True)

    mask = st.session_state.contacts['BranchName'].isin(st.session_state.selected_branches)
    st.session_state.filtered_contacts = pd.DataFrame(columns=st.session_state.contacts.columns)
    st.session_state.filtered_contacts = pd.concat(
    [st.session_state.filtered_contacts, st.session_state.contacts[mask]],
    ignore_index=True)

    mask = st.session_state.IdDf['BranchName'].isin(st.session_state.selected_branches)
    st.session_state.filtered_IDs = pd.DataFrame(columns=st.session_state.IdDf.columns)
    st.session_state.filtered_IDs = pd.concat(
    [st.session_state.filtered_IDs, st.session_state.IdDf[mask]],
    ignore_index=True
)

# display to beinformed
# st.write(st.session_state.selected_branches)
# st.write(st.session_state.filtered_events)
# st.write(st.session_state.filtered_contacts)
prev_selected_tab = st.session_state.selected_tab
st.session_state.selected_tab = st.sidebar.radio("Select Tab", ("Calendar", "Edit Calendar", "Edit Contact", "Show Calls"))
if st.session_state.selected_tab != prev_selected_tab:
    st.experimental_rerun()

def calendar_tab():
    current_date = datetime.now()
    iso_date = current_date.strftime('%Y-%m-%d')
    calendar_options = {
                'headerToolbar': {
                    'left': 'dayGridMonth',
                    'center': 'title',
                },
                'navLinks': 'true',
                'initialDate': iso_date,
                "slotMinTime": "08:00:00",
                "slotMaxTime": "18:00:00",
                'initialView': 'dayGridMonth',
            }

    col1, col2 = st.columns([3, 1])

    with col1:
        new_calendar_events = [] 
        for index, row in st.session_state.filtered_events.iterrows():
            if isinstance(row['Start'], pd.Timestamp) and isinstance(row['End'], pd.Timestamp):
                new_event = {
                    'title': f"{row['Name']} {row['ResourceId']} - {row['Region']} - {row['BranchName']}",
                    'name':row['Name'],
                    'color': row['Color'],  
                    'start': row['Start'].strftime("%Y-%m-%d %H:%M"), 
                    'end': row['End'].strftime("%Y-%m-%d %H:%M"),      
                    'resourceId': row['ResourceId'], 
                    'Region': row['Region'], 
                    'BranchName': row['BranchName'], 
                    'email': row['Email'] 
                }
            else:
                new_event = {
                    'title': f"{row['Name']} {row['ResourceId']} - {row['Region']} - {row['BranchName']}",
                    'name':row['Name'],
                    'color': row['Color'],  
                    'start': row['Start'], 
                    'end': row['End'],      
                    'resourceId': row['ResourceId'], 
                    'Region': row['Region'], 
                    'BranchName': row['BranchName'], 
                    'email': row['Email'] 
                }
            new_calendar_events.append(new_event)
        st.session_state.state = calendar(events=new_calendar_events, options=calendar_options)
    event_click_data = st.session_state.state.get('eventClick')
    with col2:
        st.write("")
        st.write("")
        st.write("")
        st.write("")
        with st.form("Info:", clear_on_submit=True):           
            if event_click_data and 'event' in event_click_data:
                event = st.session_state.state['eventClick']['event']
                st.write(f"<h3 style='color: {event['backgroundColor']}; font-family: Arial;'><strong>{event['title']}</h3>", unsafe_allow_html=True)
                formatted_start = datetime.strptime(event['start'], "%Y-%m-%dT%H:%M:%S%z").strftime("%Y-%m-%d %H:%M")
                formatted_end = datetime.strptime(event['end'], "%Y-%m-%dT%H:%M:%S%z").strftime("%Y-%m-%d %H:%M")
                st.write(
                    f"<div style='display: flex; font-family: Arial;'>"
                    f"<p><strong>Start:</strong></p>"
                    f"<p>{formatted_start}</p>"
                    f"</div>"
                    f"<div style='display: flex; font-family: Arial;'>"
                    f"<p><strong>End:</strong></p>"
                    f"<p>{formatted_end}</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                    # Additional event details
                    # st.write(f"<p style='font-family: Arial;'>Region: {event['extendedProps']['Region']}</p>", unsafe_allow_html=True)
                    # st.write(f"<p style='font-family: Arial;'>Resource ID: {st.session_state.state['eventClick']['el']['fcSeg']['eventRange']['def']['resourceIds']}</p>", unsafe_allow_html=True)
                    # st.write(f"<p style='font-family: Arial;'><strong>Region: </p>", unsafe_allow_html=True)
                    # st.write(f"<p style='font-family: Arial;'>{event['extendedProps']['Region']}</p>", unsafe_allow_html=True)
                    # st.write(f"<p style='font-family: Arial;'><strong>Resource ID: </p>", unsafe_allow_html=True)
                    # st.write(f"<p style='font-family: Arial;'>{state['eventClick']['el']['fcSeg']['eventRange']['def']['resourceIds']}</p>", unsafe_allow_html=True)

                if ("Team" in event['extendedProps']['name']):

                    event_name = event['extendedProps']['name']
                    team_part, lead_part = event_name.split('/')
                    matching_contact = st.session_state.filtered_contacts[
                        (st.session_state.filtered_contacts["Team"] == team_part) | (st.session_state.filtered_contacts["Team"] == lead_part)
                    ]
                    # matching_contact = st.session_state.filtered_contacts[st.session_state.filtered_contacts["Team"].isin([event['extendedProps']['Name']])]
                    # matching_contact = pd.DataFrame(st.session_state.filtered_contacts[st.session_state.filtered_contacts["Team"] == event['title']].copy())
                    if len(matching_contact)>0:
                        leadNames = matching_contact.loc[matching_contact["Team"].str.contains("Lead"), "Name"].tolist()
                        teamNames = matching_contact.loc[matching_contact["Team"].str.contains("Team"), "Name"].tolist()
                        Phones = matching_contact["Phone"].tolist()
                        leadPhones = matching_contact.loc[matching_contact["Team"].str.contains("Lead"), "Phone"].tolist()
                        teamPhones = matching_contact.loc[matching_contact["Team"].str.contains("Team"), "Phone"].tolist()
                        emails = matching_contact["Email"].tolist()
                        leadEmails = matching_contact.loc[matching_contact["Team"].str.contains("Lead"), "Email"].tolist()
                        teamEmails = matching_contact.loc[matching_contact["Team"].str.contains("Team"), "Email"].tolist()

                        st.write("<p style='font-family: Arial;'><strong>Lead Contacts:</strong></p>", unsafe_allow_html=True)
                        for lead_name, lead_Phone, lead_email in zip(leadNames, leadPhones, leadEmails):
                            st.write(f"<p style='font-family: Arial;'>{lead_name} |<br>{lead_Phone} |<br> {lead_email}</p>", unsafe_allow_html=True)
                        
                        st.write("<p style='font-family: Arial;'><strong>Team Contacts:</strong></p>", unsafe_allow_html=True)
                        for team_name, team_Phone, team_email in zip(teamNames, teamPhones, teamEmails):
                            st.write(f"<p style='font-family: Arial;'>{team_name} |<br>{team_Phone} |<br>{team_email}</p>", unsafe_allow_html=True)
                    else:
                        st.write("No matching contact found for the event.")
                else:
                    matching_contact = []
                    matching_rows = st.session_state.filtered_contacts[st.session_state.filtered_contacts["Email"] == event['extendedProps']['email']]

                    if not matching_rows.empty:
                        matching_contact = matching_rows.iloc[0]
                    if len(matching_contact)>0:
                        st.write(f"<p style='font-family: Arial;'><strong>Phone: </strong>{matching_contact['Phone']}</p>", unsafe_allow_html=True)
                        st.write(f"<p style='font-family: Arial;'><strong>Email: </strong>{matching_contact['Email']}</p>", unsafe_allow_html=True)
                    else:
                        st.write("No matching contact found for the event.")
                st.form_submit_button("")
def event_tab():
        if st.session_state.filtered_events is None or len(st.session_state.filtered_events) == 0 :
            one_hour = timedelta(hours=1)   
            new_end_time = datetime.now() + one_hour
            newEventsDF = pd.DataFrame([{"Name": "", "Color": "", "Start": datetime.now(),
            "End":  new_end_time, "ResourceId": "", 'Region':'', "BranchName":st.session_state.selected_branches[0], "Email":"@guardianfueltech.com", "ManagerPhone":"0000000000", "RowID":""}])
        else:
            st.session_state.filtered_events["Start"] = pd.to_datetime(st.session_state.filtered_events["Start"])
            st.session_state.filtered_events["End"] = pd.to_datetime(st.session_state.filtered_events["End"])
    # with st.expander("******Add Event Form******", expanded=True):
        with st.form("add_event_form"):
            # width = 800
            # inwidth = 500
            
            # gb = GridOptionsBuilder.from_dataframe(st.session_state.filtered_events)
            # gb.configure_column("Name",editable=True)
            # gb.configure_column("Color",editable=True)
            # gb.configure_column("Start",editable=True)
            # gb.configure_column("End",editable=True)
            # gb.configure_column("ResourceId",editable=True)
            # gb.configure_column("Region",editable=True)
            # gb.configure_column("BranchName",editable=True)
            # gb.configure_column("Email",editable=True)
            # gb.configure_column("ManagerPhone",editable=True)
            # gridOptions = gb.build()

            # # Display the AgGrid
            # data = AgGrid(
            #     st.session_state.filtered_events,
            #     gridOptions=gridOptions,
            #     enable_enterprise_modules=True,
            #     allow_unsafe_jscode=True,
            #     update_mode=GridUpdateMode.SELECTION_CHANGED,
            #     columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
            # )
            newEventsDF = pd.DataFrame(st.session_state.filtered_events, columns=['Technician_ID', 'Color', 'Start', 'End', 'Name', 'ResourceId', 'Region', 'BranchName', 'Email', 'ManagerPhone'])
            newEventsDF = st.data_editor(
                newEventsDF,
                column_config={
                    "Name": st.column_config.TextColumn(
                        "Name",
                        help="Name",
                        # width=inwidth/6,
                    ),
                    "Start": st.column_config.DatetimeColumn(
                        "Event Start Date",
                        help="Event Start Date",
                        format="D MMM YYYY, H:mm",
                        step=60,
                        # width=inwidth/6,
                    ),
                    "End": st.column_config.DatetimeColumn(
                        "Event End Date",
                        help="Event End Date",
                        format="D MMM YYYY, H:mm",
                        step=60,
                        # width=inwidth/6,
                    ),
                    "Color": st.column_config.SelectboxColumn(
                        "Event Color",
                        help="Event Color",
                        # width=inwidth/6,
                        options= ["blue", "orange", "red", "purple", "darkgreen", "gold", "magenta"]
                    ),                    
                    # techid alphabetical order st.session_state.filtered_IDs["Technician_ID"].tolist()
                    "Technician_ID": st.column_config.SelectboxColumn(
                        "Technician_ID",
                        help="Technician_ID",
                        # width=inwidth/6,
                        options= st.session_state.filtered_IDs["Technician_ID"].tolist()
                    ),
                    "ResourceId": st.column_config.SelectboxColumn(
                        "Resource ID",
                        help="Resource ID",
                        # width=inwidth/6,
                        options= ["Primary", "Backup"]
                    ),
                    "Region": st.column_config.SelectboxColumn(
                        "Region",
                        help="Region",
                        # width=inwidth/6,
                        options= ["North", "South", "None"]
                    ),
                    "BranchName": st.column_config.TextColumn(
                        "BranchName",
                        help="BranchName",
                        # width=inwidth/6,
                        default = st.session_state.selected_branches[0],
                        disabled=True
                    ),
                    "Email": st.column_config.TextColumn(
                        "Email",
                        help="Email",
                        # width=inwidth/6,
                    ),
                    "ManagerPhone": st.column_config.NumberColumn(
                        "OnCallManagerPhoneNumber",
                        help="OnCallManagerPhoneNumber",
                        # width=inwidth/6,
                        format='%s'
                    ),
                    "RowID": st.column_config.NumberColumn(
                        "RowID",
                        help="RowID",
                        # width=inwidth/6,
                        disabled=True
                    ),
                },
                hide_index=True,
                # width=width,
                num_rows="dynamic",
                key="addCalendar"
            )
            newEventsDF = newEventsDF.dropna()

            st.error("PLEASE do not submit 00:00:00 midnight!")
            st.warning("Kindly reminder, this Button will temporarily store on your device")
            calendarSubmit = st.form_submit_button("Calendar Submit")
            if calendarSubmit:
                phone_pattern = re.compile(r'^\d{10}$')
                if "ManagerPhone" in st.session_state.filtered_events.columns and not st.session_state.filtered_events["ManagerPhone"].empty:
                    if not st.session_state.filtered_events["ManagerPhone"].apply(lambda x: bool(phone_pattern.match(str(x)))).all():
                        st.error("Invalid phone number format. Please enter a 10-digit number.")
                
                mask = st.session_state.calendar_events['BranchName'].isin(st.session_state.selected_branches)
                originbranchdata = st.session_state.calendar_events[mask]
                if(len(originbranchdata)!=0):
                    if all(isinstance(value, pd.Timestamp) for value in st.session_state.filtered_events["End"]):
                        st.session_state.filtered_events["Start"] = st.session_state.filtered_events["Start"].dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                        st.session_state.filtered_events["End"] = st.session_state.filtered_events["End"].dt.strftime("%Y-%m-%d %H:%M:%S.%f")    
                    
                    insert_condition = newEventsDF["RowID"].isna()
                    st.session_state.insertrowEvent = newEventsDF[insert_condition]

                    delete_condition = ~originbranchdata["RowID"].isin(newEventsDF["RowID"])
                    st.session_state.deleterowEvent = originbranchdata[delete_condition]
                    # st.write(delete_condition,originbranchdata,originbranchdata[~delete_condition],newEventsDF[~insert_condition])
                    st.session_state.updaterowEvent = originbranchdata[~delete_condition].set_index('RowID').compare(newEventsDF[~insert_condition].set_index('RowID'), align_axis='index')
                else:
                    st.session_state.insertrowEvent = newEventsDF
                st.write("origin", originbranchdata,"updateevent", st.session_state.updaterowEvent, "insertevent", st.session_state.insertrowEvent, "deleteevent", st.session_state.deleterowEvent)
                st.session_state.filtered_events = newEventsDF
                with st.spinner("please wait"):
                    time.sleep(10)
                    st.session_state.changed = True    
                st.experimental_rerun()
def contact_tab():
    # with st.expander("******Edit Contact Form******", expanded=True):
        if len(st.session_state.filtered_contacts) == 0:
            st.session_state.filtered_contacts = pd.DataFrame([{'BranchName':st.session_state.selected_branches[0], "Name": "", "Phone": "0000000000", "Email": "@guardianfueltech.com", "Team": "", "RowID":""}])
        with st.form(key="edit_contact_form"):
            # width = 800
            # inwidth = 500
            newContactDF = st.data_editor(
                st.session_state.filtered_contacts,
                column_config={
                    "BranchName": st.column_config.TextColumn(
                        "BranchName",
                        help="BranchName",
                        # width=inwidth/6,
                        default=st.session_state.selected_branches[0],
                        disabled=True
                    ),
                    "Name": st.column_config.TextColumn(
                        "Name",
                        help="Name",
                        # width=inwidth/6,
                    ),
                    "Phone": st.column_config.TextColumn(
                        "Phone",
                        help="Phone",
                        # width=inwidth/6,
                    ),
                    "Email": st.column_config.TextColumn(
                        "Email",
                        help="Email",
                        # width=inwidth/6,
                    ),
                    "Team": st.column_config.TextColumn(
                        "Team",
                        help="Team",
                        # width=inwidth/6,
                    ),
                    "RowID": st.column_config.NumberColumn(
                        "RowID",
                        help="RowID",
                        # width=inwidth/6,
                        disabled=True
                    ),
                },
                hide_index=True,
                # width=750,
                num_rows="dynamic",
                key="editContacts"
            )

            st.warning("Kindly reminder, this Button will temporarily store on your device")
            contactsSubmit = st.form_submit_button("Contacts Submit")
            if not st.session_state.filtered_contacts.empty:
                if contactsSubmit:
                    mask = st.session_state.contacts['BranchName'].isin(st.session_state.selected_branches)
                    originbranchdata = st.session_state.contacts[mask]
                    if(len(originbranchdata)!=0):
                        insert_condition = newContactDF["RowID"].isna()
                        st.session_state.insertrowContact = newContactDF[insert_condition]

                        delete_condition = ~originbranchdata["RowID"].isin(newContactDF["RowID"])
                        st.session_state.deleterowContact = originbranchdata[delete_condition]
                        st.session_state.updaterowContact = originbranchdata[~delete_condition].set_index('RowID').compare(newContactDF[~insert_condition].set_index('RowID'), align_axis='index')
                    else:
                        st.session_state.insertrowContact = newContactDF
                    st.write("break here \n origin", originbranchdata,"updateContact", st.session_state.updaterowContact, "insertContact", st.session_state.insertrowContact, "deleteContact", st.session_state.deleterowContact)
                    st.session_state.filtered_contacts = newContactDF
                    with st.spinner("please wait"):
                        time.sleep(10)
                        st.session_state.changed = True
                    st.experimental_rerun()

def simulate_operation(duration, description):
    progress_text = f"{description}. Please wait. {duration/60} mins"
    st.text(progress_text)
    progress_bar = st.progress(0)
    for percent_complete in range(1, 101):
        time.sleep(duration / 100)
        progress_bar.progress(percent_complete)

def call_tab():
    df = pd.read_csv("assignCall.csv")
    st.table(df)
    for index, row in df.iterrows():
        st.subheader(f"Processing Row {row['tech_phone_number']}")
        simulate_operation(15, "Sending out message")
        simulate_operation(900, "Waiting for technician to reply")
        simulate_operation(15, "Calling Technician")
        simulate_operation(900, "Waiting for technician to reply")
        simulate_operation(15, "Elevate to manager reply overtime")

if st.sidebar.button("AssignCall"):
    flask_thread = threading.Thread(target=run_assignCall_app)
    flask_thread.start()
    st.success("call has send!")
    time.sleep(1)
    st.experimental_rerun()

if 'flask_thread' in st.session_state:
    output = st.session_state.flask_thread
    if output:
        st.text("Flask App Output/Error:")
        st.code(output, language='text')

if len(st.session_state.select_branches) == 0:
    st.warning("please select a branch")
else:
    if st.session_state.selected_tab == "Calendar":
        calendar_tab()
    if(len(selected_branches)>=2):
        st.sidebar.error("Can't edit with multiple selected branches! Please select one branch only")
        st.error("Can't edit with multiple selected branches! Please select one branch only")
    else:
        if st.session_state.changed:
            st.sidebar.success("Caution! Pressing this button will update both contacts and events in database.")
            if st.sidebar.button("Update to database"):
                if len(st.session_state.insertrowEvent)>0:
                    st.session_state.calendar_events = insertEvents(st.session_state.insertrowEvent)
                if len(st.session_state.deleterowEvent)>0:
                    st.session_state.calendar_events = deleteEvents(st.session_state.deleterowEvent)
                if len(st.session_state.updaterowEvent)>0:
                    st.session_state.calendar_events = updateEvents(st.session_state.updaterowEvent)
                
                if len(st.session_state.insertrowContact)>0:
                    st.session_state.contacts = insertContact(st.session_state.insertrowContact)
                if len(st.session_state.deleterowContact)>0:
                    st.session_state.contacts = deleteContact(st.session_state.deleterowContact)
                if len(st.session_state.updaterowContact)>0:
                    st.session_state.contacts = updateContact(st.session_state.updaterowContact)

                mask = st.session_state.calendar_events['BranchName'].isin(st.session_state.selected_branches)    
                st.session_state.filtered_events = pd.DataFrame(columns=st.session_state.calendar_events.columns)
                st.session_state.filtered_events = pd.concat(
                [st.session_state.filtered_events, st.session_state.calendar_events[mask]],
                ignore_index=True)

                mask = st.session_state.contacts['BranchName'].isin(st.session_state.selected_branches)
                st.session_state.filtered_contacts = pd.DataFrame(columns=st.session_state.contacts.columns)
                st.session_state.filtered_contacts = pd.concat(
                [st.session_state.filtered_contacts, st.session_state.contacts[mask]],
                ignore_index=True
                )
                csv = createCsv()
                st.session_state.changed = False
                st.experimental_rerun()
        
        if st.session_state.selected_tab == "Edit Calendar":
            event_tab()
        if st.session_state.selected_tab == "Edit Contact":
            contact_tab()
        if st.session_state.selected_tab == "Show Calls":
            call_tab()
                


                

