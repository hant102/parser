import os
import re
import json
import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
from urllib.parse import urljoin

from genres import (
    GENRE_ACTION,
    GENRE_ADVENTURE,
    GENRE_RPG,
    GENRE_STRATEGY,
    GENRE_SIMULATION,
)

URL_TEMPLATE = "https://m.moreigr.com"
FILE_NAME = "output.csv"
OUTPUT_FOLDER = 'output'

def get_last_parsed_page():
    if not os.path.exists("last_parsed_page.txt"):
        data = {'last_parsed_pages': {}, 'page_ranges': {}}
        with open("last_parsed_page.txt", "w") as file:
            json.dump(data, file)

        return data['last_parsed_pages'], data['page_ranges']

    with open("last_parsed_page.txt", "r") as file:
        data = json.load(file)

        if not data:
            return {}, {}

        last_parsed_pages = data.get('last_parsed_pages', {})
        page_ranges = data.get('page_ranges', {})
        return last_parsed_pages, page_ranges


def save_last_parsed_page(last_parsed_pages, page_ranges):
    data = {
        'last_parsed_pages': last_parsed_pages,
        'page_ranges': page_ranges,
    }

    with open("last_parsed_page.txt", "w") as file:
        json.dump(data, file)

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|/]', '_', filename.replace(' ', '_'))

def sanitize_image_filename(filename):
    return re.sub(r'[\\/*?:"<>|/]', '_', os.path.basename(filename))

def download_torrent(url, game_folder):
    torrent_url = urljoin(URL_TEMPLATE, url)
    torrent_filename = os.path.join(game_folder, os.path.basename(url))
    with open(torrent_filename, 'wb') as torrent_file:
        torrent_response = requests.get(torrent_url)
        torrent_file.write(torrent_response.content)


def parse_game_page(url):
    r = requests.get(url)
    soup = bs(r.text, "lxml")
    game_data = {}

    title_element = soup.find('div', class_='full-story').find('h1')
    game_data['title'] = title_element.text.strip().replace('скачать торрент', '') if title_element else ''

    description_element = soup.find('div', class_='full').find_all('p')
    game_data['description'] = '\n'.join(p.text.strip() for p in description_element)

    razrab_element = soup.select_one('li.second:-soup-contains("Разработчик"), li.first:-soup-contains("Разработчик")')
    game_data['razrab'] = razrab_element.get_text(strip=True) if razrab_element else ''

    janr_element = soup.select_one('li.second:-soup-contains("Категория"), li.first:-soup-contains("Категория")')
    game_data['janr'] = janr_element.get_text(strip=True) if janr_element else ''

    god_element = soup.select_one('li.first:-soup-contains("Год выхода"), li.second:-soup-contains("Год выхода")')
    game_data['god'] = god_element.get_text(strip=True) if god_element else ''

    langint_element = soup.select_one('li.first:-soup-contains("Язык интерфейса"), li.second:-soup-contains("Язык интерфейса")')
    game_data['language_interface'] = langint_element.get_text(strip=True) if langint_element else ''

    langvoice_element = soup.select_one('li.second:-soup-contains("Язык озвучки"), li.first:-soup-contains("Язык озвучки")')
    game_data['language_voice'] = langvoice_element.get_text(strip=True) if langvoice_element else ''

    langsubtitle_element = soup.select_one('li.first:-soup-contains("Субтитры"), li.second:-soup-contains("Субтитры")')
    game_data['language_subtitle'] = langsubtitle_element.get_text(strip=True) if langsubtitle_element else ''

    tabletka_element = soup.select_one('li.first:-soup-contains("Таблетка"), li.second:-soup-contains("Таблетка")')
    game_data['tabletka'] = tabletka_element.get_text(strip=True) if tabletka_element else ''

    screenshots_div = soup.find('div', class_='screens')
    game_data['screenshots_html'] = str(screenshots_div) if screenshots_div else ''

    torrent_tag = soup.find('a', class_='button4', string='СКАЧАТЬ ТОРРЕНТ')
    game_data['torrent_url'] = torrent_tag['href'] if torrent_tag else ''

    info_div = soup.find('div', class_='orazdache')

    if info_div:
        edition_element = info_div.find(string=re.compile(r'Тип издания:'))
        version_element = info_div.find(string=re.compile(r'Версия игры:'))

        if edition_element:
            game_data['edition'] = edition_element.split(':')[-1].strip()
        else:
            game_data['edition'] = 'N/A'

        if version_element:
            game_data['version'] = version_element.split(':')[-1].strip()
        else:
            game_data['version'] = 'N/A'

    if 'edition' not in game_data:
        game_data['edition'] = 'N/A'

    if 'version' not in game_data:
        game_data['version'] = 'N/A'


    instr_element = soup.find('td', class_='tdname', string='Инструкция по установке:')
    instr_data = ''

    if instr_element:
        instr_data_element = instr_element.find_next('td', class_='tdzhach')
        if instr_data_element:
            if instr_data_element.find('br'):
                for br_tag in instr_data_element.find_all('br'):
                    br_tag.replace_with('\n')
                instr_data = instr_data_element.get_text(strip=True)
            else:
                instr_data = instr_data_element.get_text(strip=True, separator='\n')

    game_data['installation_instructions'] = instr_data


    return game_data



def parse(url=URL_TEMPLATE):
    print("Available categories:")
    print("1. Action Games")
    print("2. Adventure Games")
    print("3. RPG Games")
    print("4. Strategy Games")
    print("5. Simulation Games")
    print("6. All categories")

    category_choice = input("Enter the number of the category to parse or '6' for all categories: ")

    if category_choice != '6':
        category_url_map = {
            '1': GENRE_ACTION,
            '2': GENRE_ADVENTURE,
            '3': GENRE_RPG,
            '4': GENRE_STRATEGY,
            '5': GENRE_SIMULATION,
        }
        category_url = category_url_map.get(category_choice)
        if category_url:
            url = urljoin(URL_TEMPLATE, category_url)

    last_parsed_pages, page_ranges = get_last_parsed_page()
    current_category_url = url

    print(f"Last parsed page for {current_category_url}: {last_parsed_pages.get(current_category_url, 1)}")

    pages_to_parse = input("Enter the page range to parse (e.g., '2-6') or enter a single page number: ")

    if "-" in pages_to_parse:
        try:
            start_page, end_page = map(int, pages_to_parse.split("-"))
            if start_page < 1 or end_page < start_page:
                raise ValueError("Invalid range. Start page should be greater than 0 and end page should be greater than or equal to start page.")
            parse_single_page = False
        except ValueError:
            print("Invalid input. Parsing first page only.")
            parse_single_page = True
    else:
        try:
            start_page = int(pages_to_parse)
            if start_page < 1:
                raise ValueError("Invalid page number. Page number should be greater than 0.")
            end_page = start_page
            parse_single_page = True
        except ValueError:
            print("Invalid input. Parsing first page only.")
            parse_single_page = True

    result_list = {
        'href': [], 'title': [], 'description': [], 'janr': [], 'god': [],
        'language_interface': [], 'language_voice': [], 'language_subtitle': [],
        'tabletka': [], 'razrab': [], 'version': [], 'edition': [], 'installation_instructions': []
    }

    if parse_single_page:
        page_range = (start_page, end_page)
    else:
        page_range = (last_parsed_pages.get(current_category_url, 1) + 1, last_parsed_pages.get(current_category_url, 1) + (end_page - start_page) + 1)

    for page_num in range(page_range[0], page_range[1] + 1):
        page_url = f"{current_category_url}/page/{page_num}/"
        r = requests.get(page_url)
        soup = bs(r.text, "lxml")
        vacancies_names = soup.find_all('div', class_='short-story')

        if not vacancies_names:
            break

        print(f"Parsing page: {page_num}")

        for name in vacancies_names:
            vacancy_url = name.a['href']
            game_data = parse_game_page(vacancy_url)
            result_list['href'].append(vacancy_url)
            result_list['title'].append(game_data['title'])
            result_list['description'].append(game_data['description'])
            result_list['janr'].append(game_data['janr'])
            result_list['god'].append(game_data['god'])
            result_list['language_interface'].append(game_data['language_interface'])
            result_list['language_voice'].append(game_data['language_voice'])
            result_list['language_subtitle'].append(game_data['language_subtitle'])
            result_list['tabletka'].append(game_data['tabletka'])
            result_list['razrab'].append(game_data['razrab'])
            result_list['edition'].append(game_data['edition'])
            result_list['version'].append(game_data['version'])
            result_list['installation_instructions'].append(game_data['installation_instructions'])

    last_parsed_pages[current_category_url] = page_range[1]
    page_ranges[current_category_url] = {
        'start_page': page_range[0],
        'end_page': page_range[1],
    }

    save_last_parsed_page(last_parsed_pages, page_ranges)

    return result_list


def main():
    result_list = parse()
    df = pd.DataFrame(data=result_list)
    df.to_csv(FILE_NAME)

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    for game_title, group_data in df.groupby('title'):
        sanitized_title = sanitize_filename(game_title)
        game_folder = os.path.join(OUTPUT_FOLDER, sanitized_title)
        os.makedirs(game_folder, exist_ok=True)

        output_txt_file = os.path.join(game_folder, f'{sanitized_title}.txt')
        txt_content = group_data.to_string(index=False, header=True, index_names=False, line_width=-1, justify='left', col_space=4)
        with open(output_txt_file, 'w', encoding='utf-8') as f:
            f.write(txt_content)

        game_url = group_data['href'].iloc[0]
        game_data = parse_game_page(game_url)

        screenshots_div = bs(game_data['screenshots_html'], "html.parser")
        a_tags = screenshots_div.find_all('a')
        for a_tag in a_tags:
            img_url = a_tag['href']
            img_full_url = urljoin(URL_TEMPLATE, img_url)
            img_filename = os.path.join(game_folder, sanitize_image_filename(img_url))
            with open(img_filename, 'wb') as img_file:
                img_response = requests.get(img_full_url)
                img_file.write(img_response.content)

        if game_data['torrent_url']:
            download_torrent(game_data['torrent_url'], game_folder)

    print(f'CSV file "{FILE_NAME}" has been converted to separate TXT files for each game in the folder "{OUTPUT_FOLDER}".')


if __name__ == "__main__":
    main()