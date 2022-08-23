# EIA Drilling Productivity Report - https://www.eia.gov/petroleum/drilling/
# pulls in xlsx from EIA to get production (oil and gas) by basin

# BTU explains EA methodology calculating rig productivity, legacy production changes : https://btuanalytics.com/crude-oil-pricing/eia-drilling-productivity-report-misleading-market/


import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import datetime
from bs4 import BeautifulSoup as bs
import requests

# web-scrape data release dates
def dpr_release_dates():
        """ web-scrape release dates of 
        most recent and upcoming production data update """
        base_url = 'https://www.eia.gov/petroleum/drilling/'
        response = requests.get(base_url)
        soup = bs(response.content, 'html.parser')
        release_div = soup.find("div",{"class":"release-dates"})
        for i in release_div:
                release_date = i.find_next('span').text
                if len(release_date) > 21:
                        print(release_date)
        print("Most recent Release includes EIA estimate data for the following month")
dpr_release_dates()


# prep variables
url = 'https://www.eia.gov/petroleum/drilling/xls/dpr-data.xlsx'

sheets = ['Anadarko Region',
        'Permian Region',
        'Appalachia Region',
        'Bakken Region',
        'Eagle Ford Region',
        'Haynesville Region',
        'Niobrara Region']

# Read file, all sheets, into a dict
dict_all = pd.read_excel(url,
        sheet_name=sheets, engine='openpyxl',
        header=[0,1],
        parse_dates=True)


### Prep workbook - concatenate sheets & convert into DataFrame ###
for sheet in dict_all.keys():
    # add column for region, remove excess string
    dict_all[sheet][('', 'Region')] = sheet[:-7]
    # drop columns
    dict_all[sheet] = dict_all[sheet].drop(
                    [
                    ('Oil (bbl/d)', 'Production per rig'),
                    ('Oil (bbl/d)', 'Legacy production change'),
                    ('Natural gas (Mcf/d)', 'Production per rig'),
                    ('Natural gas (Mcf/d)', 'Legacy production change')
                    ],
                    axis=1)
    # rename columns
    dict_all[sheet].columns = dict_all[sheet].columns.to_flat_index()
    dict_all[sheet] = dict_all[sheet].rename(columns={
                                                (sheet, 'Month'):('', 'date'),
                                                ('Oil (bbl/d)', 'Total production'):('', 'crude production (bbl/d)'),
                                                ('Natural gas (Mcf/d)', 'Total production'):('', 'gas production (mcf/d)')
                                                })
    dict_all[sheet].columns = pd.MultiIndex.from_tuples(dict_all[sheet].columns)
    # convert MultiIndex columns to single index
    dict_all[sheet] = dict_all[sheet].droplevel(0,axis=1)

# concatenate sheets into DataFrame
df = pd.concat(dict_all, ignore_index=True)

# add year and month columns
df['year'] = pd.DatetimeIndex(df['date']).year
df['month'] = pd.DatetimeIndex(df['date']).month

# convert timestamp to object to remove timestamp in pivot table analysis
df['date'] = pd.to_datetime(df['date']).dt.date




### ----- Charting and analysis ----- ###
sns.set_theme(style="darkgrid")


## Monthly crude production by basin ##
sns.lineplot(data=df, x='date', y='crude production (bbl/d)', hue='Region', ci=None)
plt.show()


## Latest month's production and changes ##
d# pull latest 2 months and prior year month of data
df_comp_months = df[(df['date'] == df['date'].iloc[-1]) |
                      (df['date'] == df['date'].iloc[-2]) |
                      (df['date'] == df['date'].iloc[-13])]
# create pivot table
pivot = pd.pivot_table(data=df_comp_months,
                       index=['Region'],
                       columns=['date'],
                       values='crude production (bbl/d)',
                       aggfunc='mean')
# clean and sort
pivot = pivot.astype(int).round()
pivot = pivot.sort_values(by=df['date'].iloc[-1], ascending=False)
# add summary columns
pivot['MoM change'] = pivot.iloc[:,2] - pivot.iloc[:,1]
pivot['MoM pct change'] = (((pivot.iloc[:,2] / pivot.iloc[:,1]) - 1) * 100).round(2).astype(str) + '%'
pivot['YoY change'] = pivot.iloc[:,2] - pivot.iloc[:,0]
pivot['YoY pct change'] = (((pivot.iloc[:,2] / pivot.iloc[:,0]) - 1) * 100).round(2).astype(str) + '%'


def show_summary():
        """ show pivot table summary data"""
        dpr_release_dates()
        print("\n----- Units in barrels per day (bbl/d) -----")
        return pivot
show_summary()


# latest month production across all basins
df_latest_month = df_comp_months[df_comp_months['date'] == df_comp_months['date'].max()]
df_latest_month = df_latest_month.sort_values(by=['crude production (bbl/d)'], ascending=False)
sns.barplot(x='Region', y='crude production (bbl/d)', data=df_latest_month).set(title=str(df_comp_months['date'].max()) + ' crude production by region')
plt.xticks(rotation=45)
plt.show()




### Top 2 producing regions in latest full year ###

# get latest full year of production data: latest_year
if df['date'].max().month == 12:
    latest_year = df['year'].max()
else:
    latest_year = df['year'].max() - 1

# dataframe of yearly production by region
df_yearly_prod = df.groupby(['Region', 'year'])['crude production (bbl/d)'].mean().reset_index()

# subset yearly production dataframe to get last 2 years for analysis
df_oil_prod_latest_year = df_yearly_prod[df_yearly_prod['year'] == latest_year].sort_values('crude production (bbl/d)', ascending=False)
df_oil_prod_prior_year = df_yearly_prod[df_yearly_prod['year'] == latest_year - 1].sort_values('crude production (bbl/d)', ascending=False)
# pull production levels from prior year based on above subsets
current_top_producer_prior_year = df_oil_prod_prior_year[df_oil_prod_prior_year['Region'] == df_oil_prod_latest_year.iloc[0][0]]['crude production (bbl/d)'].item()
second_top_producer_prior_year = df_oil_prod_prior_year[df_oil_prod_prior_year['Region'] == df_oil_prod_latest_year.iloc[1][0]]['crude production (bbl/d)'].item()
# analyze YoY changes for top 2 producing regions
top_inc_dec = df_oil_prod_latest_year.iloc[0][2] - current_top_producer_prior_year
second_inc_dec = df_oil_prod_latest_year.iloc[1][2] - second_top_producer_prior_year


print('\nIn ' + str(latest_year) + ', ' + df_oil_prod_latest_year.iloc[0][0] + ' was the largest oil producing basin in the US, pumping ' +
        "{0:.3g}".format(df_oil_prod_latest_year.iloc[0][2]) + ' bbls/d.')

print('------ Production in the basin changed by ' +
        "{:.0%}".format(df_oil_prod_latest_year.iloc[0][2] / current_top_producer_prior_year - 1) + 
        ', or ' + "{0:.3g}".format(top_inc_dec) + ' bbls/d compared to ' + str(latest_year - 1) + '------\n')


print('The 2nd largest producing region, ' + df_oil_prod_latest_year.iloc[1][0] + ', pumped ' +
        "{0:.3g}".format(df_oil_prod_latest_year.iloc[1][2]) + 'bbls/d.')

print('------ Production in the basin changed by ' +
        "{:.0%}".format(df_oil_prod_latest_year.iloc[1][2] / second_top_producer_prior_year - 1) + 
        ', or ' + "{0:.3g}".format(second_inc_dec) + ' bbls/d compared to ' + str(latest_year - 1) + '------')

