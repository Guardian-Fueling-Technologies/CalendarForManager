from streamlit_calendar import calendar
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import time
import pyodbc
import re
import os

server = os.environ.get("serverGFT")
database = os.environ.get("databaseGFT")
username = os.environ.get("usernameGFT")
password = os.environ.get("passwordGFT")
SQLaddress = os.environ.get("addressGFT")

def getAll():
    conn_str = f"DRIVER={SQLaddress};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"
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
      ,[ResourceId]
      ,[Region]
      ,[BranchName]
      ,[Email]
      ,CAST([RowID] AS NVARCHAR(MAX)) AS RowIDString
        FROM [GFT].[dbo].[CF_OnCall_Calendar_Events]
        '''    
    cursor.execute(sql_query)
    result = cursor.fetchall()
    data = [list(row) for row in result]
    eventDf = pd.DataFrame(data, columns=['Name', 'Color', 'Start', 'End', 'ResourceId', 'Region', 'BranchName', 'Email', 'RowID'])

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
    contactDf = pd.DataFrame(data, columns=['BranchName', 'Name', 'Phone', 'Email', 'Team', 'RowID'])

    cursor.close()
    conn.close()
    return branchDf, contactDf, eventDf

def updateEvents(branchName, eventDf):
    conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # delete_query = "DELETE FROM [GFT].[dbo].[CF_OnCall_Contact] WHERE BranchName = ?"
    # cursor.execute(delete_query, (branchName,))
    # conn.commit()
    
    sql_query = '''
        SELECT [Name]
            ,[Color]
            ,[Start]
            ,[End]
            ,[ResourceId]
            ,[Region]
            ,[BranchName]
            ,[Email]
            ,[RowID]
        FROM [GFT].[dbo].[CF_OnCall_Calendar_Events]
        WHERE BranchName = ? 
    '''
    cursor.execute(sql_query, (branchName),)
    sql_query = cursor.fetchall()
    rows_transposed = [sql_query for sql_query in zip(*sql_query)]
    cc = pd.DataFrame(dict(zip(['Name', 'Color', 'Start', 'End', 'ResourceId', 'Region', 'BranchName'
      ,'Email', 'RowID'], rows_transposed)))

    update_query = '''
    UPDATE [GFT].[dbo].[CF_OnCall_Calendar_Events]
    SET [Name] = ?,
        [Color] = ?,
        [Start] = ?,
        [End] = ?,
        [ResourceId] = ?,
        [Region] = ?,
        [BranchName] = ?,
        [Email] = ?
    WHERE [RowID] = ?
    '''
    for index, row in eventDf.iterrows():
        values = (
            row['Name'],
            row['Color'],
            str(row['Start']),
            str(row['End']),
            row['ResourceId'],
            row['Region'],
            row['BranchName'],
            row['Email'],
            row['RowID']
        )
        cursor.execute(update_query, values)
        conn.commit()
    # eventDf = eventDf.dropna()
    # data = eventDf[['Name', 'Color', 'Start', 'End', 'ResourceId', 'Region', 'BranchName','Email']].values.tolist()
    # data = [row for row in data]
    # insert_query = "INSERT INTO [GFT].[dbo].[CF_OnCall_Calendar_Events] ([Name], [Color], [Start], [End], [ResourceId], [Region], [BranchName], [Email]) VALUES (?,?,?,?,?,?,?,?)"
    # if data:
    #     cursor.executemany(insert_query, data)
    #     conn.commit()

    sql_query = '''
        SELECT [Name]
            ,[Color]
            ,[Start]
            ,[End]
            ,[ResourceId]
            ,[Region]
            ,[BranchName]
            ,[Email]
            ,[RowID]
        FROM [GFT].[dbo].[CF_OnCall_Calendar_Events]
        WHERE BranchName = ? 
    '''
    cursor.execute(sql_query, (branchName),)
    sql_query = cursor.fetchall()
    rows_transposed = [sql_query for sql_query in zip(*sql_query)]
    cc = pd.DataFrame(dict(zip(['Name', 'Color', 'Start', 'End', 'ResourceId', 'Region', 'BranchName'
      ,'Email', 'RowID'], rows_transposed)))
    
def insertEvents(branchName, eventDf):
    conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    delete_query = "DELETE FROM [GFT].[dbo].[CF_OnCall_Calendar_Events] WHERE BranchName = ?"
    cursor.execute(delete_query, (branchName),)
    conn.commit()

    data = eventDf[['Name', 'Color', 'Start', 'End', 'ResourceId', 'Region', 'BranchName','Email']].values.tolist()
    data = [row for row in data]
    insert_query = "INSERT INTO [GFT].[dbo].[CF_OnCall_Calendar_Events] ([Name], [Color], [Start], [End], [ResourceId], [Region], [BranchName], [Email]) VALUES (?,?,?,?,?,?,?,?)"
    if data:
        cursor.executemany(insert_query, data)
        conn.commit()

    sql_query = '''
        SELECT [Name]
            ,[Color]
            ,[Start]
            ,[End]
            ,[ResourceId]
            ,[Region]
            ,[BranchName]
            ,[Email]
            ,[RowID]
        FROM [GFT].[dbo].[CF_OnCall_Calendar_Events]
        WHERE BranchName = ? 
    '''
    cursor.execute(sql_query, (branchName),)
    sql_query = cursor.fetchall()
    rows_transposed = [sql_query for sql_query in zip(*sql_query)]
    cc = pd.DataFrame(dict(zip(['Name', 'Color', 'Start', 'End', 'ResourceId', 'Region', 'BranchName'
      ,'Email', 'RowID'], rows_transposed)))

st.set_page_config(page_title="On Call Schedule Calendar", page_icon="📆", layout="wide")

calendar_options = {}
if "branch" not in st.session_state:
    st.session_state.branch, st.session_state.contacts, st.session_state.calendar_events = getAll()
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
if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = "Calendar"

st.sidebar.subheader("BranchName")
# branch_names_set = set(event['BranchName'] for event in st.session_state.calendar_events)
selected_branches = st.sidebar.multiselect("Select Branches", st.session_state.branch['BranchName'], key="select_branches")
if selected_branches != st.session_state.selected_branches:
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
    ignore_index=True
)


# display to beinformed
# st.write(st.session_state.selected_branches)
# st.write(st.session_state.filtered_events)
# st.write(st.session_state.filtered_contacts)
prev_selected_tab = st.session_state.selected_tab
st.session_state.selected_tab = st.sidebar.radio("Select Tab", ("Calendar", "Edit Calendar", "Edit Contact"))
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
                    'start': row['Start'].strftime("%Y-%m-%d %H:%M:%S"), 
                    'end': row['End'].strftime("%Y-%m-%d %H:%M:%S"),      
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
            st.session_state.filtered_events = pd.DataFrame([{"Name": "", "Color": "", "Start": datetime.now(),
            "End":  new_end_time, "ResourceId": "", 'Region':'', "BranchName":"", "Email":"@guardianfueltech.com"}])
        else:
            st.session_state.filtered_events["Start"] = pd.to_datetime(st.session_state.filtered_events["Start"])
            st.session_state.filtered_events["End"] = pd.to_datetime(st.session_state.filtered_events["End"])
        
    # with st.expander("******Add Event Form******", expanded=True):
        with st.form("add_event_form"):
            # width = 800
            # inwidth = 500
            st.session_state.filtered_events = st.data_editor(
                st.session_state.filtered_events,
                column_config={
                    "Name": st.column_config.TextColumn(
                        "Name",
                        help="Name",
                        # width=inwidth/6,
                    ),
                    "Start": st.column_config.DatetimeColumn(
                        "Event Start Date",
                        help="Event Start Date",
                        # width=inwidth/6,
                    ),
                    "End": st.column_config.DatetimeColumn(
                        "Event End Date",
                        help="Event End Date",
                        # width=inwidth/6,
                    ),
                    "Color": st.column_config.SelectboxColumn(
                        "Event Color",
                        help="Event Color",
                        # width=inwidth/6,
                        options= ["blue", "orange", "red", "purple", "darkgreen", "gold", "magenta"]
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

            st.error("PLEASE do not submit 00:00:00 midnight!")
            st.warning("Kindly reminder, this Button will temporarily store on your device")
            calendarSubmit = st.form_submit_button("Calendar Submit")
            if calendarSubmit:
                if all(isinstance(value, pd.Timestamp) for value in st.session_state.filtered_events["End"]):
                    st.session_state.filtered_events["Start"] = st.session_state.filtered_events["Start"].dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                    st.session_state.filtered_events["End"] = st.session_state.filtered_events["End"].dt.strftime("%Y-%m-%d %H:%M:%S.%f")    

                with st.spinner("please wait"):
                    time.sleep(1)
                st.session_state.changed = True    
                # st.experimental_rerun()

def contact_tab():
    # with st.expander("******Edit Contact Form******", expanded=True):
        if len(st.session_state.filtered_contacts) == 0:
            st.session_state.filtered_contacts = pd.DataFrame([{'BranchName':st.session_state.selected_branches[0], "Name": "", "Phone": "000-000-0000", "Email": "@guardianfueltech.com", "Team": "", "RowID":""}])
        with st.form(key="edit_contact_form"):
            # width = 800
            # inwidth = 500
            st.session_state.filtered_contacts = st.data_editor(
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
                    st.session_state.changed = True
                    st.experimental_rerun()
            
if len(st.session_state.select_branches) == 0:
    st.warning("please select a branch")
else:
    if st.session_state.selected_tab == "Calendar":
        calendar_tab()
    if(len(selected_branches)>=2):
        st.sidebar.error("Can't edit with multiple selected branches! Please select one branch only")
        st.error("Can't edit with multiple selected branches! Please select one branch only")
    else:
        if st.session_state.selected_tab == "Edit Calendar":
            event_tab()
        if st.session_state.selected_tab == "Edit Contact":
            contact_tab()
        if st.session_state.changed:
            st.sidebar.success("Caution! Pressing this button will update both contacts and events in database.")
            if st.sidebar.button("Update to database"):
                insertEvents(st.session_state.selected_branches, st.session_state.filtered_events)
                st.session_state.changed = False
                # st.experimental_rerun()
