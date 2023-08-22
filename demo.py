from streamlit_calendar import calendar
from datetime import datetime
import streamlit as st
import pandas as pd
import time

st.set_page_config(page_title="On Call Schedule Calendar", page_icon="📆", layout="wide")
# st.write("hiTest")
calendar_options = {}
if "contacts" not in st.session_state:
    st.session_state.contacts = [
        {   
            'BranchShortName':'FTL',
            "name": "Bob",
            "phone": "000-000-0000",
            "email": "primaryBob@guardianfueltech.com",
            "team": ""
        },
        {
            'BranchShortName':'FTL',
            "name": "John",
            "phone": "000-000-0000",
            "email": "primaryJohn@guardianfueltech.com",
            "team": ""
        },
        {
            'BranchShortName':'FTL',
            "name": "Boo",
            "phone": "000-000-0000",
            "email": "primaryBoo@guardianfueltech.com",
            "team": ""
        },
        {
            'BranchShortName':'FTL',
            "name": "Charlie",
            "phone": "000-000-0000",
            "email": "primaryCharlie@guardianfueltech.com",
            "team": ""
        },
        {
            'BranchShortName':'SAN',
            "name": "BaD",
            "phone": "000-000-0000",
            "email": "",
            "team": "Team 3"
        },
        {
            'BranchShortName':'SAN',
            "name": "Good",
            "phone": "000-000-0000",
            "email": "",
            "team": "Team 3"
        },
        {
            'BranchShortName':'SAN',
            "name": "Brian",
            "phone": "000-000-0000",
            "email": "",
            "team": "Team 3"
        },
        {
            'BranchShortName':'SAN',
            "name": "Mike",
            "phone": "000-000-0000",
            "email": "",
            "team": "Team 3"
        },
        {
            'BranchShortName':'SAN',
            "name": "Dave",
            "phone": "000-000-0000",
            "email": "",
            "team": "Lead 2"
        },
        {
            'BranchShortName':'SAN',
            "name": "AMy",
            "phone": "000-000-0000",
            "email": "",
            "team": "Lead 2"
        }
    ]
    csv_filename = "contact.csv"
    df = pd.DataFrame(st.session_state.contacts)
    df.to_csv(csv_filename, index=False)

if "calendar_events" not in st.session_state:
    st.session_state.calendar_events = [
        {'Name': 'Team 3/Lead 2', 'color': 'magenta', 'start': '2023-07-19T00:00:00', 'end': '2023-07-21T00:00:00', 'resourceId': 'Primary', 'Region':'North', 'BranchShortName':'SAN', 'email':''}, 
        {'Name': 'Team 3/Lead 2', 'color': 'magenta', 'start': '2023-07-21T00:00:00', 'end': '2023-07-27T00:00:00', 'resourceId': 'Primary', 'Region':'North', 'BranchShortName':'SAN', 'email':''}, 
        {'Name': 'Team 2/Lead 1', 'color': 'magenta', 'start': '2023-07-28T00:00:00', 'end': '2023-08-03T00:00:00', 'resourceId': 'Primary', 'Region':'North', 'BranchShortName':'SAN', 'email':''}, 
        {'Name': 'Team 1/Lead 1', 'color': 'magenta', 'start': '2023-08-04T00:00:00', 'end': '2023-08-10T00:00:00', 'resourceId': 'Primary', 'Region':'North', 'BranchShortName':'SAN', 'email':''}, 
        {'Name': 'Team 4/Lead 1', 'color': 'magenta', 'start': '2023-08-11T00:00:00', 'end': '2023-08-17T00:00:00', 'resourceId': 'Primary', 'Region':'North', 'BranchShortName':'SAN', 'email':''}, 
        {'Name': 'Team 3/Lead 1', 'color': 'magenta', 'start': '2023-08-18T00:00:00', 'end': '2023-08-24T00:00:00', 'resourceId': 'Primary', 'Region':'North', 'BranchShortName':'SAN', 'email':''}, 
        {'Name': 'Team 2/Lead 2', 'color': 'magenta', 'start': '2023-08-25T00:00:00', 'end': '2023-08-31T00:00:00', 'resourceId': 'Primary', 'Region':'North', 'BranchShortName':'SAN', 'email':''},
    
        {'Name': 'Bob', 'color': 'blue', 'start': '2023-08-11T00:00:00', 'end': '2023-08-17T00:00:00', 'resourceId': 'Primary', 'Region':'North', 'BranchShortName':'FTL', 'email':'primaryBob@guardianfueltech.com'}, 
        {'Name': 'John', 'color': 'blue', 'start': '2023-08-18T00:00:00', 'end': '2023-08-24T00:00:00', 'resourceId': 'Primary', 'Region':'North', 'BranchShortName':'FTL', 'email':'primaryJohn@guardianfueltech.com'}, 
        {'Name': 'Boo', 'color': 'blue', 'start': '2023-08-25T00:00:00', 'end': '2023-08-31T00:00:00', 'resourceId': 'Primary', 'Region':'North', 'BranchShortName':'FTL', 'email':'primaryBoo@guardianfueltech.com'}
    ]
    csv_filename = "calendar_events.csv"
    df = pd.DataFrame(st.session_state.calendar_events)
    df.to_csv(csv_filename, index=False)
if 'selected_branches' not in st.session_state:
    st.session_state.selected_branches = ['SAN']
if 'filtered_events' not in st.session_state:
    st.session_state.filtered_events = [event for event in st.session_state.calendar_events if event['BranchShortName'] in st.session_state.selected_branches]
if 'filtered_contacts' not in st.session_state:
    st.session_state.filtered_contacts = [event for event in st.session_state.contacts if event['BranchShortName'] in st.session_state.selected_branches]

if "branch_names_set" not in st.session_state:
    st.session_state.branch_names_set = {"BIR", "FTL", "FTM", "GULF", "JAX", "LAF", "SAN", "SAV", "TAM", "TALLY"}

new_branch_name = st.sidebar.text_input("Enter New Branch Name:")
if new_branch_name:
    st.session_state.branch_names_set.add(new_branch_name)

st.markdown('<style>div.sidebar{width: 250px;}</style>', unsafe_allow_html=True)
st.sidebar.subheader("BranchName")
branch_names_set = set(event['BranchShortName'] for event in st.session_state.calendar_events)
unique_branch_names = sorted(list(branch_names_set.union(st.session_state.branch_names_set)))
selected_branches = st.sidebar.multiselect("Select Branches", unique_branch_names, default=['SAN'], key="select_branches")
if selected_branches != st.session_state.selected_branches:
    st.session_state.selected_branches = selected_branches
    st.session_state.filtered_events = [event for event in st.session_state.calendar_events if event['BranchShortName'] in selected_branches]
    st.session_state.filtered_contacts = [event for event in st.session_state.contacts if event['BranchShortName'] in selected_branches]
    for event in st.session_state.filtered_events:
        event["start"] = event["start"].isoformat() if isinstance(event["start"], datetime) else event["start"]
        event["end"] = event["end"].isoformat() if isinstance(event["end"], datetime) else event["end"]

# display to beinformed
# st.write(st.session_state.selected_branches)
# st.write(st.session_state.filtered_events)
# st.write(st.session_state.filtered_contacts)

st.session_state.selected_tab = st.sidebar.radio("Select Tab", ("Calendar", "Edit Calendar", "Edit Contact"))
    
def calendar_tab():
    calendar_options = {
                'headerToolbar': {
                    'left': 'today',
                    'center': 'title',
                },
                'navLinks': 'true',
                'initialDate': '2023-07-01',
                "slotMinTime": "08:00:00",
                "slotMaxTime": "18:00:00",
                'initialView': 'dayGridMonth',
            }

    col1, col2 = st.columns([3, 1])

    with col1:
        new_calendar_events = [] 
        for event in st.session_state.filtered_events:
            new_event = event.copy() 
            new_event['title'] = f"{event['Name']} {event['resourceId']} - {event['Region']} - {event['BranchShortName']}"
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
                color = event['backgroundColor']
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

                if(event['extendedProps']['BranchShortName'] == "SAN"):
                    stripped_title = event['title'].replace(event['extendedProps']['BranchShortName'], "").strip()
                    matching_contacts = [contact for contact in st.session_state.filtered_contacts if contact["team"] in event['extendedProps']['Name']]
                    if matching_contacts:
                        leadNames = [contact['name'] for contact in matching_contacts if "Lead" in contact['team']]
                        teamNames = [contact['name'] for contact in matching_contacts if "Team" in contact['team']]
                        phones = [contact['phone'] for contact in matching_contacts]
                        leadPhones = [contact['phone'] for contact in matching_contacts if "Lead" in contact['team']]
                        teamPhones = [contact['phone'] for contact in matching_contacts if "Team" in contact['team']]
                        emails = [contact['email'] for contact in matching_contacts]
                        leadEmails = [contact['email'] for contact in matching_contacts if "Lead" in contact['team']]
                        teamEmails = [contact['email'] for contact in matching_contacts if "Team" in contact['team']]
                        st.write("<p style='font-family: Arial;'><strong>Lead Contacts:</strong></p>", unsafe_allow_html=True)
                        for lead_name, lead_phone, lead_email in zip(leadNames, leadPhones, leadEmails):
                            st.write(f"<p style='font-family: Arial;'>{lead_name} |<br>{lead_phone} |<br> {lead_email}</p>", unsafe_allow_html=True)
                        
                        st.write("<p style='font-family: Arial;'><strong>Team Contacts:</strong></p>", unsafe_allow_html=True)
                        for team_name, team_phone, team_email in zip(teamNames, teamPhones, teamEmails):
                            st.write(f"<p style='font-family: Arial;'>{team_name} |<br>{team_phone} |<br>{team_email}</p>", unsafe_allow_html=True)
                    else:
                        st.write("No matching contact found for the event.")
                else:
                    matching_contact = next((contact for contact in st.session_state.contacts if contact["email"] == event['extendedProps']['email']), None)
                    if matching_contact:
                        st.write(f"<p style='font-family: Arial;'><strong>Phone: </strong>{matching_contact['phone']}</p>", unsafe_allow_html=True)
                        st.write(f"<p style='font-family: Arial;'><strong>Email: </strong>{matching_contact['email']}</p>", unsafe_allow_html=True)
                    else:
                        st.write("No matching contact found for the event.")

                st.form_submit_button("")
def event_tab():
    # with st.expander("******Add Event Form******", expanded=True):
        if st.session_state.filtered_events == None:
            st.session_state.filtered_events = {"Name": "", "color": "", "start": "",
                "end": "", "resourceId": "", 'Region':'', "BranchShortName":""}    
        with st.form("add_event_form"):
            # width = 800
            # inwidth = 500
            for event in st.session_state.filtered_events:
                if isinstance(event["start"], str):
                    event["start"] = datetime.strptime(event["start"], "%Y-%m-%dT%H:%M:%S")
                if isinstance(event["end"], str):
                    event["end"] = datetime.strptime(event["end"], "%Y-%m-%dT%H:%M:%S")


            st.session_state.filtered_events = st.data_editor(
                st.session_state.filtered_events,
                column_config={
                    "Name": st.column_config.TextColumn(
                        "Name",
                        help="Name",
                        # width=inwidth/6,
                    ),
                    "start": st.column_config.DatetimeColumn(
                        "Event Start DateTime",
                        help="Event Start DateTime",
                        # width=inwidth/6,
                        step=1
                    ),
                    "end": st.column_config.DatetimeColumn(
                        "Event End Date",
                        help="Event End Date",
                        # width=inwidth/6,
                        step=1
                    ),
                    "color": st.column_config.SelectboxColumn(
                        "Event Color",
                        help="Event Color",
                        # width=inwidth/6,
                        options= ["blue", "orange", "red", "purple", "darkgreen", "gold", "magenta"]
                    ),
                    "resourceId": st.column_config.SelectboxColumn(
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
                    "BranchShortName": st.column_config.SelectboxColumn(
                        "BranchShortName",
                        help="BranchShortName",
                        # width=inwidth/6,
                        options= selected_branches
                    ),
                },
                hide_index=True,
                # width=width,
                num_rows="dynamic",
                key="addCalendar"
            )
            for event in st.session_state.filtered_events:
                event["start"] = event["start"].isoformat() if isinstance(event["start"], datetime) else event["start"]
                event["end"] = event["end"].isoformat() if isinstance(event["end"], datetime) else event["end"]

            calendarSubmit = st.form_submit_button("Calendar Submit")
            if calendarSubmit:
                with st.spinner("please wait"):
                    time.sleep(1)
                for event in st.session_state.filtered_events:
                    event["start"] = event["start"].isoformat() if isinstance(event["start"], datetime) else event["start"]
                    event["end"] = event["end"].isoformat() if isinstance(event["end"], datetime) else event["end"]

                st.experimental_rerun()

def contact_tab():
    # with st.expander("******Edit Contact Form******", expanded=True):
        with st.form("edit_contact_form"):
            # width = 800
            # inwidth = 500
            if len(st.session_state.filtered_contacts) == 0 :
                st.session_state.filtered_contacts = [{'BranchShortName':'', "name": "", "phone": "000-000-0000", "email": "@guardianfueltech.com", "team": ""}]

            st.session_state.filtered_contacts = st.data_editor(
                st.session_state.filtered_contacts,
                column_config={
                    "BranchShortName": st.column_config.SelectboxColumn(
                        "BranchShortName",
                        help="BranchShortName",
                        # width=inwidth/6,
                        options= selected_branches
                    ),
                    "name": st.column_config.TextColumn(
                        "name",
                        help="name",
                        # width=inwidth/6,
                    ),
                    "phone": st.column_config.TextColumn(
                        "phone",
                        help="phone",
                        # width=inwidth/6,
                    ),
                    "email": st.column_config.TextColumn(
                        "email",
                        help="email",
                        # width=inwidth/6,
                    ),
                    "team": st.column_config.TextColumn(
                        "team",
                        help="team",
                        # width=inwidth/6,
                    ),
                },
                hide_index=True,
                # width=750,
                num_rows="dynamic",
                key="editContacts"
            )
            contactsSubmit = st.form_submit_button("Contacts Submit")
            if contactsSubmit:
                with st.spinner("please wait"):
                    time.sleep(1)
                st.experimental_rerun()
            
            
if st.session_state.selected_tab == "Calendar":
    calendar_tab()
elif st.session_state.selected_tab == "Edit Calendar":
    event_tab()
elif st.session_state.selected_tab == "Edit Contact":
    contact_tab()

