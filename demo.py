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
flowUsername = os.environ.get("flowUsername")
flowPassword = os.environ.get("flowPassword")

def getEvent(cursor):
    selectQuery = '''
       SELECT [Primary],[Back-up1],[Back-up2],[Back-up3],[FSM1],[FSM2],[DisplayName],[Color],[Start],[End],[Region],[BranchName],[RowID]      
       FROM [GFT].[dbo].[CF_OnCall_Calendar_Events] WITH(NOLOCK)
    '''
    cursor.execute(selectQuery)
    result = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    data = [list(row) for row in result]
    return pd.DataFrame(data, columns=columns)

def getTechnicianContact(cursor):
    selectQuery = '''
        SELECT [Technician_ID], [Name], [Phone], [Email], [Group_ID], [BranchName], [RowID]
        FROM [GFT].[dbo].[CF_OnCall_Contact] WITH(NOLOCK);
    '''
    cursor.execute(selectQuery)
    result = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    data = [list(row) for row in result]
    return pd.DataFrame(data, columns=columns)

def createCursor():
    conn_str = f"DRIVER={SQLaddress};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"
    conn = pyodbc.connect(conn_str)
    return conn, conn.cursor()

def createCsv():
    conn, cursor = createCursor()
    eventDf = getEvent(cursor)
    contactDf = getTechnicianContact(cursor)
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
    conn, cursor = createCursor()

    sql_query = '''
        SELECT DISTINCT RTrim(Wennsoft_Branch) as Wennsoft_Branch , Rtrim(BranchName) as BranchName FROM [dbo].[GFT_SV00077_Ext] WITH(NOLOCK)
        WHERE Wennsoft_Branch <> 'Pensacola' AND BranchName NOT IN ('Pensacola', 'Corporate', 'Guardian Connect');
        '''    
    cursor.execute(sql_query)
    result = cursor.fetchall()
    rows_transposed = [result for result in zip(*result)]
    branchDf = pd.DataFrame(dict(zip(['Wennsoft_Branch', 'BranchName'], rows_transposed)))

    eventDf = getEvent(cursor)
    contactDf = getTechnicianContact(cursor)

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
    conn, cursor = createCursor()
    df_columns = ["Primary","Back-up1","Back-up2","Back-up3","FSM1","FSM2", "DisplayName", "Color", "Start", "End", "Region", "BranchName", "RowID"]
    for row_id, row in eventDf.iterrows():
        if(row_id[1]=='self'):
            continue
        update_query = f'UPDATE [GFT].[dbo].[CF_OnCall_Calendar_Events] WITH(ROWLOCK) SET '
        values = []
        for col in df_columns:
            if col in row.index:
                update_query += f'[{col}] = ?, '
                values.append(row[col])

        update_query = update_query.rstrip(', ')
        update_query += ' WHERE [RowID] = ?'
        values.append(row_id[0])
        cursor.execute(update_query, values)
        conn.commit()
    eventDf = getEvent(cursor)
    
    cursor.close()
    conn.close()
    return eventDf
    
def deleteEvents(eventDf):
    conn, cursor = createCursor()

    delete_query = "DELETE FROM [GFT].[dbo].[CF_OnCall_Calendar_Events] WITH(ROWLOCK) WHERE RowID = ? ;"
    
    for index, row in eventDf.iterrows():
        row_id = row["RowID"]
        cursor.execute(delete_query, (row_id,))
        conn.commit()
    eventDf = getEvent(cursor)
    cursor.close()
    conn.close()
    return eventDf

def insertEvents(eventDf):
    conn, cursor = createCursor()
    data = eventDf[["Primary","Back-up1","Back-up2","Back-up3","FSM1","FSM2", "DisplayName", "Color", "Start", "End", "Region", "BranchName"]].values.tolist()
    data = [row for row in data]
    insert_query = "INSERT INTO [GFT].[dbo].[CF_OnCall_Calendar_Events] WITH(ROWLOCK) ([Primary],[Back-up1],[Back-up2],[Back-up3],[FSM1],[FSM2], [DisplayName], [Color], [Start], [End], [Region], [BranchName]) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
    if data:
        cursor.executemany(insert_query, data)
        conn.commit()
    eventDf = getEvent(cursor)
    cursor.close()
    conn.close()
    return eventDf

def updateContact(contactDF):
    conn, cursor = createCursor()      
    df_columns = ["Technician_ID", "Name", "Phone", "Email", "Group_ID", "Manager_email", "BranchName", "RowID"]

    for row_id, row in contactDF.iterrows():
        if(row_id[1]=='self'):
            continue
        update_query = f'UPDATE [GFT].[dbo].[CF_OnCall_Contact] WITH(ROWLOCK) SET '
        values = []
        for col in df_columns:
            if col in row.index:
                update_query += f'[{col}] = ?, '
                values.append(row[col])

        update_query = update_query.rstrip(', ')
        update_query += ' WHERE [RowID] = ?'
        values.append(row_id[0])
        cursor.execute(update_query, values)
        conn.commit()
        
    contactDf = getTechnicianContact(cursor)
    cursor.close()
    conn.close()
    return contactDf

def deleteContact(contactDf):
    conn, cursor = createCursor()
    delete_query = "DELETE FROM [GFT].[dbo].[CF_OnCall_Contact] WITH(ROWLOCK) WHERE RowID = ? ;"
    
    for index, row in contactDf.iterrows():
        row_id = row["RowID"]
        cursor.execute(delete_query, (row_id,))
        conn.commit()
    
    contactDf = getTechnicianContact(cursor)
    cursor.close()
    conn.close()
    return contactDf

def insertContact(contactDF):
    conn, cursor = createCursor()
    data = contactDF[["Technician_ID", "Name", "Phone", "Email", "Group_ID", "BranchName"]].values.tolist()
    data = [row for row in data]
    insert_query = "INSERT INTO [GFT].[dbo].[CF_OnCall_Contact] WITH(ROWLOCK) ([Technician_ID], [Role], [Name], [Phone], [Email], [Group_ID], [Region], [BranchName]) VALUES (?,?,?,?,?,?,?);"
    if data:
        cursor.executemany(insert_query, data)
        conn.commit()

    contactDf = getTechnicianContact(cursor)
    cursor.close()
    conn.close()
    return contactDf

def updateManager(flowDf):  
    conn, cursor = createCursor()
    delete_query = "DELETE FROM [GFT].[dbo].[MR_OnCall_Manager_Contact] WITH(ROWLOCK) WHERE BranchName = ?"
    cursor.execute(delete_query, st.session_state.selected_branches[0])
    conn.commit()
    
    data = flowDf[["Technician_ID", "Name", "Role", "BranchName", "Region", "Phone", "Email"]].values.tolist()
    insert_query = """
        INSERT INTO [GFT].[dbo].[MR_OnCall_Manager_Contact] WITH(ROWLOCK) ([Technician_ID], [Name], [Role], [BranchName], [Region], [Phone], [email])
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    if data:
        cursor.executemany(insert_query, data)
        conn.commit()
        
    cursor.close()
    conn.close()

def updateEscalation(flowDf):  
    conn, cursor = createCursor()
    delete_query = "DELETE FROM [GFT].[dbo].[MR_OnCall_Escalation] WITH(ROWLOCK) WHERE Branch = ?"
    cursor.execute(delete_query, st.session_state.selected_branches[0])
    conn.commit()

    
    data = flowDf[["Action", "Role", "Branch", "Region", "Escalation_Order"]].values.tolist()
    insert_query = """
        INSERT INTO [GFT].[dbo].[MR_OnCall_Escalation] WITH(ROWLOCK) ([Action], [Role], [Branch], [Region], [Escalation_Order])
        VALUES (?, ?, ?, ?, ?)
    """
    if data:
        cursor.executemany(insert_query, data)
        conn.commit()
        
    cursor.close()
    conn.close()

st.set_page_config(page_title="On Call Schedule Calendar", page_icon="📆", layout="wide")

calendar_options = {}
if "branch" not in st.session_state:
    st.session_state.branch, st.session_state.contacts, st.session_state.calendar_events, st.session_state.IdDf = getAll()
if 'changed' not in st.session_state:
    st.session_state.changed = False
if 'selected_branches' not in st.session_state:
    st.session_state.selected_branches = ['Atlanta']
if 'filtered_events' not in st.session_state:
    st.session_state.filtered_events = None
if 'filtered_contacts' not in st.session_state:
    st.session_state.filtered_contacts = None
if 'filtered_IDs' not in st.session_state:
    st.session_state.filtered_IDs = None

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
if 'show_group_contacts' not in st.session_state:
    st.session_state.show_group_contacts = False
if "login" not in st.session_state:
        st.session_state.login = False
if "flowUser" not in st.session_state:
    st.session_state.flowUser = ""
if "flowPass" not in st.session_state:
    st.session_state.flowPass = ""

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
st.session_state.selected_tab = st.sidebar.radio("Select Tab", ("Calendar", "Edit Calendar", "Edit Technician Contact", "Edit Manager Contact", "Escalation"))
if st.session_state.selected_tab != prev_selected_tab:
    st.rerun()

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
                    'title': f"{row['DisplayName']} - {row['Region']} - {row['BranchName']}",
                    'name':row['DisplayName'],
                    'color': row['Color'],  
                    'start': row['Start'].strftime("%Y-%m-%d %H:%M"), 
                    'end': row['End'].strftime("%Y-%m-%d %H:%M"),      
                    'Region': row['Region'], 
                    'BranchName': row['BranchName'],
                    "Technician_ID": row['Primary'],
                    "Back-up1":row['Back-up1'],
                    "Back-up2":row['Back-up2'],
                    "Back-up3":row['Back-up3'],
                    "FSM1":row['FSM1'],
                    "FSM2":row['FSM2'],
                }
            else:
                new_event = {
                    'title': f"{row['DisplayName']} - {row['Region']} - {row['BranchName']}",
                    'DisplayName':row['DisplayName'],
                    'color': row['Color'],  
                    'start': row['Start'], 
                    'end': row['End'],      
                    'Region': row['Region'], 
                    'BranchName': row['BranchName'],
                    "Technician_ID": row['Primary'],
                    "Back-up1":row['Back-up1'],
                    "Back-up2":row['Back-up2'],
                    "Back-up3":row['Back-up3'],
                    "FSM1":row['FSM1'],
                    "FSM2":row['FSM2'],
                }
            new_calendar_events.append(new_event)
        st.session_state.state = calendar(events=new_calendar_events, options=calendar_options)
    event_click_data = st.session_state.state.get('eventClick')
    with col2:
        st.write("")
        st.write("")
        st.write("")
        st.write("")      
        if event_click_data and 'event' in event_click_data:
            event = st.session_state.state['eventClick']['event']
            st.write(f"<h3 style='color: {event['backgroundColor']}; font-family: Arial;'><strong>{event['title']}</h3>", unsafe_allow_html=True)
            formatted_start = datetime.strptime(event['start'], "%Y-%m-%dT%H:%M:%S%z").strftime("%Y-%m-%d %H:%M")
            formatted_end = datetime.strptime(event['end'], "%Y-%m-%dT%H:%M:%S%z").strftime("%Y-%m-%d %H:%M")
            event = event['extendedProps']
            # st.write(event)
            backup1 = event.get('Back-up1', None)
            backup2 = event.get('Back-up2', None)
            backup3 = event.get('Back-up3', None)
            fsm1 = event.get('FSM1', None)
            fsm2 = event.get('FSM2', None)
            # region = event.get('Region', None)
            additional_info = ""
            if backup1 or backup2 or backup3 or fsm1 or fsm2:
                additional_info += "<div style='font-family: Arial;'>"
                additional_info += "<p><strong>Additional Info:</strong></p>"
                if backup1:
                    additional_info += f"<p>Back-up1: {backup1}</p>"
                if backup2:
                    additional_info += f"<p>Back-up2: {backup2}</p>"
                if backup3:
                    additional_info += f"<p>Back-up3: {backup3}</p>"
                if fsm1:
                    additional_info += f"<p>FSM1: {fsm1}</p>"
                if fsm2:
                    additional_info += f"<p>FSM2: {fsm2}</p>"
                additional_info += "</div>"

            
            st.write(
                f"<div style='display: flex; font-family: Arial;'>"
                f"<p><strong>Start:</strong></p>"
                f"<p>{formatted_start}</p>"
                f"</div>"
                f"<div style='display: flex; font-family: Arial;'>"
                f"<p><strong>End:</strong></p>"
                f"<p>{formatted_end}</p>"
                f"</div>"
                f"{additional_info}",
                unsafe_allow_html=True
            )
                # Additional event details
                # st.write(f"<p style='font-family: Arial;'>Region: {event['extendedProps']['Region']}</p>", unsafe_allow_html=True)
                # st.write(f"<p style='font-family: Arial;'>Resource ID: {st.session_state.state['eventClick']['el']['fcSeg']['eventRange']['def']['resourceIds']}</p>", unsafe_allow_html=True)
                # st.write(f"<p style='font-family: Arial;'><strong>Region: </p>", unsafe_allow_html=True)
                # st.write(f"<p style='font-family: Arial;'>{event['extendedProps']['Region']}</p>", unsafe_allow_html=True)
                # st.write(f"<p style='font-family: Arial;'><strong>Resource ID: </p>", unsafe_allow_html=True)
                # st.write(f"<p style='font-family: Arial;'>{state['eventClick']['el']['fcSeg']['eventRange']['def']['resourceIds']}</p>", unsafe_allow_html=True)
            event = st.session_state.state['eventClick']['event']
            mask = (st.session_state.filtered_contacts['Group_ID'].notna()) & (st.session_state.filtered_contacts['Group_ID'].str.strip() != '')
            filtered_contacts = pd.DataFrame(st.session_state.filtered_contacts[mask])

            # matching_rows = filtered_contacts[filtered_contacts['Technician_ID'].str.contains(event['extendedProps']['Technician_ID'])]
            # print("here",matching_rows)
            if not filtered_contacts['Group_ID'].empty:
                matching_contact = filtered_contacts[filtered_contacts["Group_ID"].isin(filtered_contacts['Group_ID'])]
                if len(matching_contact) > 0:
                    if st.button("Toggle Group"):
                        # Toggle the state
                        st.session_state.show_group_contacts = not st.session_state.show_group_contacts

                    # Check the state and display accordingly
                    if st.session_state.show_group_contacts:
                        # Display group contacts
                        Names = matching_contact["Name"].tolist()
                        Phones = matching_contact["Phone"].tolist()
                        emails = matching_contact["Email"].tolist()
                        group_id_context = str(filtered_contacts['Group_ID']).split()[1]
                        st.write(f"<p style='font-family: Arial;'><strong>{group_id_context}'s Contacts:</strong></p>", unsafe_allow_html=True)
                        for lead_name, lead_Phone, lead_email in zip(Names, Phones, emails):
                            st.write(f"<p style='font-family: Arial;'>{lead_name} |<br>{lead_Phone} |<br> {lead_email}</p>", unsafe_allow_html=True)
                    else:
                        st.write("Group contacts are hidden.")
                else:
                    st.write("No matching contact found for the event.")
                    

                # matching_contact = []
                # matching_rows = filtered_contacts[filtered_contacts["Email"] == event['extendedProps']['email']]

                # if not matching_rows.empty:
                #     matching_contact = matching_rows.iloc[0]
                # if len(matching_contact)>0:
                #     st.write(f"<p style='font-family: Arial;'><strong>Phone: </strong>{matching_contact['Phone']}</p>", unsafe_allow_html=True)
                #     st.write(f"<p style='font-family: Arial;'><strong>Email: </strong>{matching_contact['Email']}</p>", unsafe_allow_html=True)
                # else:
                #     st.write("No matching contact found for the event.")
def event_tab():
        uploaded_file = st.file_uploader("Choose a file")
        if uploaded_file is not None:
            st.session_state.filtered_events = pd.read_csv(uploaded_file)

        if st.session_state.filtered_events is None or len(st.session_state.filtered_events) == 0 :
            one_hour = timedelta(hours=1)   
            new_end_time = datetime.now() + one_hour
            newEventsDF = pd.DataFrame([{"Primary":"","Back-up1":"","Back-up2":"","Back-up3":"","FSM1":"","FSM2":"","DisplayName": "", "Color": "", "Start": datetime.now(),
            "End":  new_end_time, 'Region':'', "BranchName":st.session_state.selected_branches[0], "RowID":""}])
        else:
            st.session_state.filtered_events["Start"] = pd.to_datetime(st.session_state.filtered_events["Start"])
            st.session_state.filtered_events["End"] = pd.to_datetime(st.session_state.filtered_events["End"])
        # st.write(st.session_state.selected_branches[0],"'s Technician IDs", str(st.session_state.filtered_IDs["Technician_ID"].tolist()))
        # newEventsDF = pd.DataFrame([{"Technician_ID":"333","DisplayName": "333", "Color": "333", "Start": datetime.now(),
        #     "End":  datetime.now(), "ResourceId": "333", 'Region':'333', "BranchName":st.session_state.selected_branches[0], "RowID":"333"}])
        # print( st.session_state.filtered_IDs["Technician_ID"].tolist())
        # gb = GridOptionsBuilder.from_dataframe(newEventsDF[["Technician_ID","DisplayName","Color","Start","End","ResourceId","Region","BranchName","RowID"]])
        # gb.configure_column("Technician_ID", editable=True, cellEditor='agSelectCellEditor', cellEditorParams={'values': st.session_state.filtered_IDs["Technician_ID"].tolist() })
        # gb.configure_column("DisplayName", editable=True)
        # gb.configure_column("Color", editable=True)
        # gb.configure_column("Start", editable=True)
        # gb.configure_column("End", editable=True)
        # gb.configure_column("ResourceId", editable=True)
        # gb.configure_column("Region", editable=True)
        # gb.configure_column("BranchName", editable=True)
        # gb.configure_column("RowID", editable=True)
        # gridOptions = gb.build()

        # # Display the AgGrid
        # data = AgGrid(
        #     newEventsDF,
        #     gridOptions=gridOptions,
        #     enable_enterprise_modules=True,
        #     allow_unsafe_jscode=True,
        #     update_mode=GridUpdateMode.SELECTION_CHANGED,
        #     columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
        # )
    # with st.expander("******Add Event Form******", expanded=True):
        with st.form("add_event_form"):
            # width = 800
            # inwidth = 500
            newEventsDF = pd.DataFrame(st.session_state.filtered_events, columns=["Primary","Back-up1","Back-up2","Back-up3","FSM1","FSM2",'DisplayName',  'Color', 'Start', 'End', 'Region', 'BranchName', 'RowID'])
            newEventsDF = st.data_editor(
                newEventsDF,
                column_config={
                    "DisplayName": st.column_config.TextColumn(
                        "NickName",
                        help="[Optional] Primary Technician Name to be shown on Calendar",
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
                    "Primary": st.column_config.SelectboxColumn(
                        "Primary",
                        help="Primary",
                        # width=inwidth/6,
                        options= st.session_state.filtered_IDs["Technician_ID"].tolist()
                    ),     
                    "Back-up1": st.column_config.SelectboxColumn(
                        "Back-up1",
                        help="Back-up1",
                        options= ['None'] + st.session_state.filtered_IDs["Technician_ID"].tolist()
                    ),    
                    "Back-up2": st.column_config.SelectboxColumn(
                        "Back-up2",
                        help="Back-up2",
                        options= ['None'] + st.session_state.filtered_IDs["Technician_ID"].tolist()
                    ),
                    "Back-up3": st.column_config.SelectboxColumn(
                        "Back-up3",
                        help="Back-up3",
                        options= ['None'] + st.session_state.filtered_IDs["Technician_ID"].tolist()
                    ),   
                    "FSM1": st.column_config.SelectboxColumn(
                        "FSM1",
                        help="FSM1",
                        options= ['None'] + st.session_state.filtered_IDs["Technician_ID"].tolist()
                    ), 
                    "FSM2": st.column_config.SelectboxColumn(
                        "FSM2",
                        help="FSM2",
                        options= ['None'] + st.session_state.filtered_IDs["Technician_ID"].tolist()
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

            columns_to_check = newEventsDF.columns.difference(['RowID', 'DisplayName', 'Back-up1', 'Back-up2', 'Back-up3', 'FSM1', 'FSM2'])
            newEventsDF = newEventsDF.dropna(subset=columns_to_check)

            st.error("PLEASE do not submit 00:00:00 midnight!    NickName is optional!")
            calendarSubmit = st.form_submit_button("Calendar Submit")
            st.warning("Kindly reminder, this Button will temporarily store on your device")
            if calendarSubmit:
                empty_displayname_mask = newEventsDF['DisplayName'].isna() | (newEventsDF['DisplayName'] == "None")
                # print(empty_displayname_mask)
                newEventsDF['Primary'] = newEventsDF['Primary'].str.strip()
                st.session_state.filtered_contacts['Technician_ID'] = st.session_state.filtered_contacts['Technician_ID'].str.strip()
                merged_data = pd.merge(newEventsDF, st.session_state.filtered_contacts, left_on='Primary', right_on='Technician_ID', how='left')
                # print(newEventsDF.loc[empty_displayname_mask, 'DisplayName'].tolist())
                # print("sec", merged_data.loc[empty_displayname_mask, 'Name'].tolist())
                newEventsDF.loc[empty_displayname_mask, 'DisplayName'] = merged_data.loc[empty_displayname_mask, 'Name']

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
                    if len(insert_condition) != 0 and len(delete_condition) != 0:
                        st.session_state.updaterowEvent = originbranchdata[~delete_condition].set_index('RowID').compare(newEventsDF[~insert_condition].set_index('RowID'), align_axis='index')
                    elif len(insert_condition) != 0:
                            st.session_state.updaterowEvent = originbranchdata[~delete_condition].set_index('RowID').compare(newEventsDF.set_index('RowID'), align_axis='index')
                    elif len(delete_condition) != 0:
                            st.session_state.updaterowEvent = originbranchdata.set_index('RowID').compare(newEventsDF[~insert_condition].set_index('RowID'), align_axis='index')
                else:
                    st.session_state.insertrowEvent = newEventsDF
                st.write("origin", originbranchdata,"updateevent", st.session_state.updaterowEvent, "insertevent", st.session_state.insertrowEvent, "deleteevent", st.session_state.deleterowEvent)
                st.session_state.filtered_events = newEventsDF
                with st.spinner("please wait"):
                    st.session_state.changed = True    
                st.rerun()

                
                
def technicianContactTab():
    # with st.expander("******Edit Contact Form******", expanded=True):
        if len(st.session_state.filtered_contacts) == 0:
            st.session_state.filtered_contacts = pd.DataFrame([{'Technician_ID':"","Name": "", "Phone": "0000000000", "Email": "@guardianfueltech.com", "Group_ID":"", 'BranchName':st.session_state.selected_branches[0], "RowID":""}])
        with st.form(key="edit_Techniciancontact_form"):
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
                    "Technician_ID": st.column_config.SelectboxColumn(
                        "Technician_ID",
                        help="Technician_ID",
                        # width=inwidth/6,
                        options= st.session_state.filtered_IDs["Technician_ID"].tolist()
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
                    "Group_ID": st.column_config.TextColumn(
                        "Group_ID",
                        help="Group_ID",
                        # width=inwidth/6,
                    ),
                    "Region": st.column_config.SelectboxColumn(
                        "Region",
                        help="Region",
                        # width=inwidth/6,
                        options= ["North", "South", "None"]
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

            columns_to_check = newContactDF.columns.difference(['RowID', 'Group_ID'])
            newContactDF = newContactDF.dropna(subset=columns_to_check)

            st.warning("Kindly reminder, this Button will temporarily store on your device")
            contactsSubmit = st.form_submit_button("Update Technicians")
            if not st.session_state.filtered_contacts.empty:
                if contactsSubmit:
                    mask = st.session_state.contacts['BranchName'].isin(st.session_state.selected_branches)
                    originbranchdata = st.session_state.contacts[mask]
                    if(len(originbranchdata)!=0):
                        insert_condition = newContactDF["RowID"].isna()
                        st.session_state.insertrowContact = newContactDF[insert_condition]

                        delete_condition = ~originbranchdata["RowID"].isin(newContactDF["RowID"])
                        st.session_state.deleterowContact = originbranchdata[delete_condition]
                        if len(insert_condition) != 0:
                            st.session_state.updaterowContact = originbranchdata[~delete_condition].set_index('RowID').compare(newContactDF[~insert_condition].set_index('RowID'), align_axis='index')
                    else:
                        st.session_state.insertrowContact = pd.DataFrame(newContactDF)
                    st.write("break here \n origin", originbranchdata,"updateContact", st.session_state.updaterowContact, "insertContact", st.session_state.insertrowContact, "deleteContact", st.session_state.deleterowContact)
                    st.session_state.filtered_contacts = newContactDF
                    with st.spinner("please wait"):
                        st.session_state.changed = True
                    st.rerun()

def ManagerContactTab():
    # Employee_ID
    conn, cursor = createCursor()
    selectQuery = '''
        SELECT 
        [Technician_ID]
        ,[Name]
        ,[Role]
        ,[BranchName]
        ,[Region]
        ,[Phone]
        ,[Email]
        ,[RowID]
        FROM [GFT].[dbo].[MR_OnCall_Manager_Contact] WITH(NOLOCK)
            WHERE [BranchName] = ?;
    '''
    cursor.execute(selectQuery, selected_branches)
    result = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    data = [list(row) for row in result]
    managerContactDf = pd.DataFrame(data, columns=columns)
    if st.session_state.login or st.session_state.flowUser == flowUsername and st.session_state.flowPass == flowPassword:
            st.session_state.login = True
            if(len(managerContactDf)==0): 
                managerContactDf = pd.DataFrame([{'Technician_ID': "",'Name': "",'Role': "",'BranchName': st.session_state.selected_branches[0],'Region': "",'Phone': "",'Email': "",'RowID': ""}])         
           # with st.expander("******Edit Contact Form******", expanded=True):
            with st.form(key="edit_Managercontact_form"):
                # width = 800
                # inwidth = 500
                managerContactDf = st.data_editor(
                    managerContactDf,
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
                        "Technician_ID": st.column_config.SelectboxColumn(
                            "Technician_ID",
                            help="Technician_ID",
                            # width=inwidth/6,
                            options= st.session_state.filtered_IDs["Technician_ID"].tolist()
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
                        "Role": st.column_config.SelectboxColumn(
                            "Role",
                            help="Role",
                            options=["FSM", "SM", "BM", "RM"],
                        ),
                        # "Group_ID": st.column_config.TextColumn(
                        #     "Group_ID",
                        #     help="Group_ID",
                        #     # width=inwidth/6,
                        # ),
                        "Region": st.column_config.SelectboxColumn(
                            "Region",
                            help="Region",
                            # width=inwidth/6,
                            options= ["North", "South", "None"]
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

                # columns_to_check = managerContactDf.columns.difference(['Group_ID'])
                # managerContactDf = managerContactDf.dropna(subset=columns_to_check)

                st.warning("Kindly reminder, this Button will directly update the database")
                contactsSubmit = st.form_submit_button("Update Managers")
                if not managerContactDf.empty:
                    if contactsSubmit:
                        with st.spinner("please wait"):
                            updateManager(managerContactDf)
                        st.rerun()
    else:
        st.title("Login Credentials")
        st.session_state.flowUser = st.text_input("Username")
        st.session_state.flowPass = st.text_input("Password", type="password")
        st.button("Submit")

def flow_tab():
    conn, cursor = createCursor()

    sql_query = '''SELECT [Action], [Role], [Branch], [Region], [Escalation_Order], [RowID]
        FROM [GFT].[dbo].[MR_OnCall_Escalation] WITH (NOLOCK)
        WHERE [Branch] = ?
        '''

    cursor.execute(sql_query, selected_branches)
    result = cursor.fetchall()
    rows_transposed = [result for result in zip(*result)]
    flowDf = pd.DataFrame(dict(zip(['Action', 'Role', 'Branch', 'Region', 'Escalation_Order','RowID'], rows_transposed)))
    
    with st.expander("View", expanded=True):
        flowDf = st.data_editor(
            flowDf,
            column_config={
                "Role": st.column_config.SelectboxColumn(
                    "Role",
                    help="Role",
                    options=["Lead", "Back-Up", "FSM", "SM", "BM", "RM"],
                    disabled=True
                ),
                "Action": st.column_config.SelectboxColumn(
                    "Action",
                    help="Action",
                    options=["Message", "Call"],
                    disabled=True
                ),
                "Branch": st.column_config.TextColumn(
                    "Branch",
                    help="Branch",
                    default=st.session_state.selected_branches[0],
                    disabled=True
                ),
                "Region": st.column_config.SelectboxColumn(
                    "Region",
                    help="Region",
                    options=["North", "South", "None"],
                    disabled=True
                ),
                "Escalation_Order": st.column_config.SelectboxColumn(
                    "Escalation_Order",
                    help="Escalation_Order",
                    disabled=True
                ),
                "RowID": st.column_config.NumberColumn(
                    "RowID",
                    help="RowID",
                    disabled=True
                ),
            },
            hide_index=True,
            width=750,
            key="view"
        )
    
    if st.session_state.login or st.session_state.flowUser == flowUsername and st.session_state.flowPass == flowPassword:
        st.session_state.login = True
        if(len(flowDf)==0):            
            flowDf = pd.DataFrame([{'Role':"", "Action": "", "Branch": st.session_state.selected_branches[0], "Region": "", "Escalation_Order":"", "RowID":""}])
        with st.form(key="edit_escalation_form"):
            flowDf = st.data_editor(
                flowDf,
                column_config={
                    "Role": st.column_config.SelectboxColumn(
                        "Role",
                        help="Role",
                        # width=inwidth/6,
                        options=["Back-up1", "Back-up2", "Back-up3", "FSM1", "FSM2", "SM", "BM", "RM"]
                    ),
                    "Action": st.column_config.SelectboxColumn(
                        "Action",
                        help="Action",
                        # width=inwidth/6,
                        options=["Message", "Call"]
                    ),
                    "Branch": st.column_config.TextColumn(
                        "Branch",
                        help="Branch",
                        # width=inwidth/6,
                        default=st.session_state.selected_branches[0],
                        disabled=True
                    ),
                    "Region": st.column_config.SelectboxColumn(
                        "Region",
                        help="Region",
                        # width=inwidth/6,
                        options= ["North", "South", "None"]
                    ),
                    "Escalation_Order": st.column_config.SelectboxColumn(
                        "Escalation_Order",
                        help="Escalation_Order",
                        # width=inwidth/6,
                        disabled=True
                    ),
                    "RowID": st.column_config.NumberColumn(
                        "RowID",
                        help="RowID",
                        # width=inwidth/6,
                        disabled=True
                    ),
                },
                hide_index=True,
                num_rows="dynamic",
                key="editContacts",
                width=700
            )
            st.warning("Kindly reminder, this Button will directly update the database max is 15 escalation")
            escalationSubmit = st.form_submit_button("Escalation Submit")
            if not flowDf.empty and escalationSubmit:
                for region in flowDf["Region"].unique():
                    region_contacts = flowDf[flowDf["Region"] == region]
                    num_contacts = len(region_contacts)
                    escalation_order = [str(i) for i in range(1, num_contacts + 1)]
                    flowDf.loc[flowDf["Region"] == region, "Escalation_Order"] = escalation_order
                flowDf = flowDf.sort_values(by=['Region', 'Escalation_Order'])
                # print(flowDf)
                updateEscalation(flowDf)
                st.rerun()
            # num_rows = st.slider('Number of rows', min_value=3, max_value=15)
            
            # columns = ['Action', 'Action Name', 'Number', 'Branch', 'Region', 'Escalation_Order']
            # df = pd.DataFrame(columns=columns)
                
            # st.write(f"Branch: {st.session_state.select_branches} Region: North")
            # grid = st.columns(3)
            # for r in range(num_rows):
            #     df = add_row(df, grid, r, st.session_state.select_branches, 'North')
            # st.write(f"Branch: {st.session_state.select_branches} Region: South")
            # grid = st.columns(3)
            # for r in range(num_rows, num_rows*2):
            #     df = add_row(df, grid, r, st.session_state.select_branches, 'South')

            # num_rows = st.slider('Number of rows', min_value=3, max_value=15, value = len(flowDf))
            # columns = ['Action', 'Role', 'Branch', 'Region']
            # df = pd.DataFrame(columns=columns)
                
            # st.write(f"Branch: {st.session_state.select_branches} Region: North")
            # grid = st.columns(3)
            # for r in range(num_rows):
            #     df = add_row(flowDf, grid, r, st.session_state.select_branches, 'North')
            # st.write(f"Branch: {st.session_state.select_branches} Region: South")
            # grid = st.columns(3)
            # for r in range(num_rows, num_rows*2):
            #     df = add_row(flowDf, grid, r, st.session_state.select_branches, 'South')

    else:
        st.title("Login Credentials")
        st.session_state.flowUser = st.text_input("Username")
        st.session_state.flowPass = st.text_input("Password", type="password")
        st.button("Submit")
        
    # df.to_excel('flowTable.xlsx', index=False)

# def simulate_operation(duration, description):
#     progress_text = f"{description}. Please wait. {duration/60} mins"
#     st.text(progress_text)
#     progress_bar = st.progress(0)
#     for percent_complete in range(1, 101):
#         time.sleep(duration / 100)
#         progress_bar.progress(percent_complete)

# def call_tab():
#     df = pd.read_csv("assignCall.csv")
#     st.table(df)
#     for index, row in df.iterrows():
#         st.subheader(f"Processing Row {row['tech_phone_number']}")
#         simulate_operation(15, "Sending out message")
#         simulate_operation(900, "Waiting for technician to reply")
#         simulate_operation(15, "Calling Technician")
#         simulate_operation(900, "Waiting for technician to reply")
#         simulate_operation(15, "Elevate to manager reply overtime")

# if st.sidebar.button("AssignCall"):
#     flask_thread = threading.Thread(target=run_assignCall_app)
#     flask_thread.start()
#     st.success("call has send!")
#     time.sleep(1)
#     st.rerun()

# if 'flask_thread' in st.session_state:
#     output = st.session_state.flask_thread
#     if output:
#         st.text("Flask App Output/Error:")
#         st.code(output, language='text')

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
                # csv = createCsv()
                st.session_state.changed = False
                st.rerun()
        
        if st.session_state.selected_tab == "Edit Calendar":
            event_tab()
        if st.session_state.selected_tab == "Edit Technician Contact":
            technicianContactTab()
        if st.session_state.selected_tab == "Edit Manager Contact":
            ManagerContactTab()
        if st.session_state.selected_tab == "Escalation":
            flow_tab()
        # if st.session_state.selected_tab == "Show Calls":
        #     call_tab()
                
