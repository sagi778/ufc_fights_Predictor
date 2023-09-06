import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from string import ascii_letters
import re
from datetime import datetime
from time import time
from tqdm import tqdm
import os
pd.set_option('display.max_columns', None)

# file management
def get_content(directory):
    content = []
    for file in os.scandir(directory):
        if file.is_dir():
            content.append(file.path + '/')
        if file.is_file():
            content.append(file.path)
    return content
def get_current_date():
    return datetime.today().strftime('%m-%d-%Y')
def get_later_date(date1, date2):
    date1_obj = datetime.strptime(date1, "%d-%m-%Y")
    date2_obj = datetime.strptime(date2, "%d-%m-%Y")

    if date1_obj > date2_obj:
        return date1
    else:
        return date2

# web scraping
def get_xml(url, data_type='xml', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'}):

    try:
        r = requests.get(url)
        soup = BeautifulSoup(r.text, data_type)
    except:
        #print('Error on: ' + url)
        return None

    return soup
def get_links(url):

    link_items = get_xml(url=url).find_all(
        'a', {'class': 'b-link b-link_style_black'})
    dates_items = get_xml(url=url).find_all(
        'span', {'class': 'b-statistics__date'})

    links = []
    dates = []
    for url, date in zip(link_items, dates_items):
        links.append(url['href'])
        dates.append(datetime.strptime(date.text.strip(),
                     "%B %d, %Y").strftime('%m-%d-%Y'))

    data = pd.DataFrame(data=zip(dates, links), columns=['date', 'event_url'])
    data.date = pd.to_datetime(data['date'], format='%m-%d-%Y')
    return data
def get_fighter_data(url):

    xml = get_xml(url=url)
    data = []
    data.append(xml.find('h2').find(
        'span', {'class': 'b-content__title-highlight'}).text.strip())  # name

    record_string = xml.find('h2').find(
        'span', {'class': 'b-content__title-record'}).text.strip()
    data.append(int(record_string[record_string.find(
        ':')+1:record_string.find('-')]))  # wins
    data.append(int(record_string.split('-')[1]))  # losses
    data.append(record_string.split('-')[2])  # draws

    stat_boxes = xml.find_all('ul')[0:3]
    for item in stat_boxes:
        for sub_item in item.contents:
            text = sub_item.text.strip().replace(" ", "").replace("\n", "")
            if len(text) > 0:
                data.append(text[text.find(':')+1:])

    data.append(get_current_date())  # last_update

    date_table_location = 7
    try:
        date_string = xml.find_all('td')[date_table_location].find_all('p')[
            1].text.strip()
        last_match = datetime.strptime(
            date_string, '%b. %d, %Y').strftime('%m-%d-%Y')
    except:
        last_match = None

    data.append(last_match)  # last_match
    data.append(url)
    return data
def get_event_date(xml):
    '''return event date'''

    item = xml.find('li', {'class': 'b-list__box-list-item'})
    string = item.get_text().strip()
    start = len('DATE:')
    date = string[start:].strip()

    return datetime.strptime(date, "%B %d, %Y").strftime("%m-%d-%Y")
def get_card(event_link):
    xml = get_xml(event_link)
    fights_url = [item['data-link'] for item in xml.find_all(
        'tr', {'class', 'b-fight-details__table-row b-fight-details__table-row__hover js-fight-details-click'})]
    names = [item.text.strip() for item in xml.find_all(
        'a', {'class', 'b-link b-link_style_black'})]
    results = [item.text for item in xml.find_all(
        'i', {'class', 'b-flag__text'})]
    wc = [item.text[:item.text.find('weight')+len('weight')].strip() for item in xml.find_all(
        'p', {'b-fight-details__table-text'}) if 'weight' in item.text]

    methods = []
    for item in xml.find_all('p', {'b-fight-details__table-text'}):
        if item.text.strip().replace('\n', '') in ['S-DEC', 'U-DEC', 'KO/TKO', 'SUB']:
            methods.append(item.text.strip().replace('\n', ''))

    data = {'fighter': names[0::2],
            'opponent': names[1::2],
            'result': results,
            'weight_class': wc,
            'method': methods,
            'date': get_event_date(xml),
            'url': fights_url}
    return data
def get_fight_general_stats(FIGHT_URL: str):

    # get keys
    KEYS_TABLE = 0
    table = get_xml(FIGHT_URL).find_all('tr')[KEYS_TABLE]
    keys = ['fighter']
    for key in table.find_all('th', {'class': 'b-fight-details__table-col'}):
        keys.append(key.text.lower().strip().replace(
            '.', '').replace(' %', '%').replace(' ', '_'))

    # get values
    VALUES_TABLE = 1
    table = get_xml(FIGHT_URL).find_all('tr')[VALUES_TABLE]
    values = []
    for item in table.find_all('p', {'class': 'b-fight-details__table-text'}):
        values.append(item.text.strip())

    fighter1_values = values[::2]
    fighter1_values[0] = fighter1_values[0][fighter1_values[0].find(
        '>')+1:]  # fix fighter's name
    fighter2_values = values[1::2]
    fighter2_values[0] = fighter2_values[0][fighter2_values[0].find(
        '>')+1:]  # fix fighter's name

    values = fighter1_values + fighter2_values
    prefix_keys = ['f_' + key for key in keys] + ['o_' + key for key in keys]
    return dict(zip(prefix_keys, values))
def get_str_perc(FIGHT_URL: str):
    xml = get_xml(FIGHT_URL)
    data = [item.text.strip().replace('\n', '').replace(' ', '')
            for item in xml.find_all('div', {'class': 'b-fight-details__charts-row'})]
    return {'f_sig_str_head': data[0][:data[0].find('%')+1],
            'f_sig_str_body': data[1][:data[1].find('%')+1],
            'f_sig_str_leg': data[2][:data[2].find('%')+1],
            'f_sig_str_dist': data[3][:data[3].find('%')+1],
            'f_sig_str_clinch': data[4][:data[4].find('%')+1],
            'f_sig_str_ground': data[5][:data[5].find('%')+1],
            'o_sig_str_head': data[0][data[0].find('Head')+len('Head'):],
            'o_sig_str_body': data[1][data[1].find('Body')+len('Body'):],
            'o_sig_str_leg': data[2][data[2].find('Leg')+len('Leg'):],
            'o_sig_str_dist': data[3][data[3].find('Distance')+len('Distance'):],
            'o_sig_str_clinch': data[4][data[4].find('Clinch')+len('Clinch'):],
            'o_sig_str_ground': data[5][data[5].find('Ground')+len('Ground'):],
            'url':FIGHT_URL}
def get_fighters_links(page_url):
    xml = get_xml(page_url)
    link_list = []
    for item in xml.find_all('a', {'class': 'b-link b-link_style_black'}):
        link_list.append(item['href'])

    return link_list
def get_signifacant_str(FIGHT_URL):
    xml = get_xml(FIGHT_URL)
    SIGNIFICANT_STR_TABLE_NUM = 2
    data = [item.text.strip().replace(' ','') for item in xml.find_all('table')][SIGNIFICANT_STR_TABLE_NUM]
    data = [item for item in data.splitlines() if item!='']
    ROW_LENGTH = int(len(data)/3)
    keys = [item.lower().replace('.','_') for item in data[:ROW_LENGTH]]
    fighter_val = data[ROW_LENGTH::2]
    opponent_val = data[ROW_LENGTH+1::2]
    data = dict(zip(keys,zip(fighter_val,opponent_val)))
    fighter_keys = [f'f_{key}_sig_str' for key in list(data.keys())]
    opponent_keys = [f'o_{key}_sig_str' for key in list(data.keys())]
    dict_data = dict(zip(fighter_keys[3:]+opponent_keys[3:],fighter_val[3:]+opponent_val[3:]))
    dict_data.update({'url':FIGHT_URL})
    return dict_data
def get_fight_result(FIGHT_URL):
    xml = get_xml(FIGHT_URL)

    fighter_data = xml.find_all('div',{'class':'b-fight-details__person'})[0].text.strip().replace('\n','')
    opponent_data = xml.find_all('div',{'class':'b-fight-details__person'})[1].text.strip().replace('\n','')
    data = {'result':fighter_data[:fighter_data.find('http://')-2],'fighter':fighter_data[fighter_data.find('>')+1:fighter_data.find('     ')]}
    data.update({'opponent':opponent_data[opponent_data.find('>')+1:opponent_data.find('     ')]})

    details = [item for item in xml.find('div',{'class':'b-fight-details__fight'}).text.replace('  ','').strip().splitlines() if item!='']
    data.update({'title':details[0],'method':details[2].strip(),'round':details[4],'time':details[6],'format':details[8],'url':FIGHT_URL})  
    return data  
def get_event_data(EVENT_URL):
    data = []
    for url in get_card(EVENT_URL)['url']:
        row = {'url':url,'event_url':EVENT_URL}
        row.update(get_fight_result(url))
        row.update(get_signifacant_str(url))
        row.update(get_str_perc(url)) 
        data.append(row)
    return data    