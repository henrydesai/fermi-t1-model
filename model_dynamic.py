#!/usr/bin/env python
# coding: utf-8

# In[9]:


import datetime
from dateutil.relativedelta import *
import pandas as pd
import streamlit as st


# ## Inputs

# In[43]:

# givens

expander = st.expander('LD Inputs')

# LD_MAX_DAYS = 120
MODEL_START_DATE = datetime.date(2026,1,1)

LD_MAX_DAYS = expander.number_input('Max LD Days', value=120)


# In[44]:


# LD calculation
BASE_RENT_KW_MONTH_USD = 45
LD_BASE_RENT_MULTIPLE = 2
daily_ld_per_mw_usd = BASE_RENT_KW_MONTH_USD*1000/30*LD_BASE_RENT_MULTIPLE


# In[45]:


# define schedule
# MUST BE IN ORDER OF DATE

SCHEDULE = []

# tranche 1
SCHEDULE.append({'date': datetime.date(2026,4,1), 'power':452, 'delay':0})
# tranche 2
SCHEDULE.append({'date': datetime.date(2026,9,1), 'power':300, 'delay':0})
#tranche 3
SCHEDULE.append({'date': datetime.date(2026,9,30), 'power':180, 'delay':0})
# tranche 4
SCHEDULE.append({'date': datetime.date(2026,12,31), 'power':160, 'delay':0})

# Power Delivered

delivery_scenario = []
delivery_elements = [
    ('Xcel Generation', 86, datetime.date(2026,4,1)),
    ('Xcel Mobile Units', 114, datetime.date(2026,4,1)),
    ('TM2500s Tranche 1', 132, datetime.date(2026,4,1)),
    ('Jersey Boys SC', 120, datetime.date(2026,4,1)),
    ('SGT-800s SC', 300, datetime.date(2026,9,1)),
    ('TM2500s Tranche 2', 180, datetime.date(2026,9,1)),
    ('Jersey Boys CC', 120, datetime.date(2026,12,31)),
    ('SGT-800s CC', 100, datetime.date(2026,12,31))
    ]

expander = st.expander('Delivery Inputs')

for element in delivery_elements:
    expander.subheader(element[0])
    col1, col2 = expander.columns(2)
    power = col1.number_input(element[0] + ' Power (MW)', value=element[1])
    date = col2.date_input(element[0] + ' Delivery Date', value=element[2])
    
    found = False
    for entry in delivery_scenario:
        if entry['date'] == date:
            entry['power'] += power
            found = True
      
    if not found:  
        delivery_scenario.append({'date': date, 'power': power})

# ## Model

# In[46]:


# get model end date
dates = []
for tranche in SCHEDULE:
    dates.append(tranche['date'])
end_date = max(dates) + datetime.timedelta(LD_MAX_DAYS)


# In[47]:


# run max model
max_output = []
for i in range((end_date-MODEL_START_DATE).days):
    date = MODEL_START_DATE + datetime.timedelta(i)
    
    power_delivered = 0
    power_delayable = 0
    cumulative_mw_delayable = 0
    for tranche in SCHEDULE:
        if date >= tranche['date']:
            power_delivered += tranche['power']
            if (date - tranche['date']).days <= LD_MAX_DAYS:
                power_delayable += tranche['power']
                cumulative_mw_delayable += tranche['power'] * (date - tranche['date']).days
    
    max_output.append({
        'date':date.isoformat(),
        'total_power_delivered': power_delivered,
        'max_mw_delayed': power_delayable,
        'max_daily_ld_liability': power_delayable*daily_ld_per_mw_usd,
        'max_cumulative_ld_liability': cumulative_mw_delayable*daily_ld_per_mw_usd
    })
    
# run scenario model
scenario_output = []
scenario_exit_message = 'Scenario Passed'
total_power_delayed = 0
for i in range((end_date-MODEL_START_DATE).days):
    date = MODEL_START_DATE + datetime.timedelta(i)
    
    power_delivered = 0
    power_commitment = 0
    power_delayed = 0
    cumulative_mw_delayed = 0
    ld_max_exceeded = False
    
    for tranche in delivery_scenario:
        if date >= tranche['date']:
            power_delivered += tranche['power']
    
    delivery_credit_balance = power_delivered
    
    for tranche in SCHEDULE:
        if date >= tranche['date']:
            power_commitment += tranche['power']
            tranche_commitment = tranche['power']
            
            if tranche_commitment > delivery_credit_balance:
                power_delayed += (tranche_commitment - delivery_credit_balance)
                st.write(power_delayed)
                total_power_delayed += power_delayed
                delivery_credit_balance = 0
                tranche['delay'] += 1
                if tranche['delay'] >= 120:
                    ld_max_exceeded = True
                    break
            else:
                delivery_credit_balance -= tranche_commitment
                tranche['delay'] = 0
    
    scenario_output.append({
        'date': date.isoformat(),
        'total_power_committed': power_commitment,
        'total_power_delivered': power_delivered,
        'power_delayed': power_delayed,
        'daily_ld_liability': power_delayed*daily_ld_per_mw_usd,
        'cumulative_ld_liability': total_power_delayed*daily_ld_per_mw_usd
    })
    
    if ld_max_exceeded:
        scenario_exit_message = 'LD Max Exceeded. Scenario Failed'
        break

# Present Model

tab1, tab2 = st.tabs(['Maximum LD Analysis', 'Scenario Analysis'])

max_df = pd.DataFrame(max_output)
max_df['date'] = pd.to_datetime(max_df['date'])
max_df = max_df.set_index('date')

monthly_max = max_df.resample('M').max()

tab1.subheader('Model Output')
tab1.dataframe(
    monthly_max
)

scenario_df = pd.DataFrame(scenario_output)
scenario_df['date'] = pd.to_datetime(scenario_df['date'])
scenario_df = scenario_df.set_index('date')

scenario_display = scenario_df.resample('M').max()

tab2.subheader('Model Output')
tab2.dataframe(
    scenario_display
)
tab2.write(scenario_exit_message)


