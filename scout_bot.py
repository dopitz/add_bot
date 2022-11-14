#!/usr/bin/env python
# -%- coding: utf-8 -%-

#===============================================
# IMMOBILIENSCOUT24 BOT
#===============================================

from __future__ import unicode_literals
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from datetime import datetime
from selenium.webdriver.chrome.options import Options

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)

import urlparse
import re
import os
import datetime
import pprint
import json
import traceback
import requests
import time
import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)

class LOGIN:
    password = 'affebananeaffebanane' #your password on Ebay small ads
    email = 'danielopitz91@gmail.com' #your email on Ebay small ads


class ME: # stuff for immobilienscouts message thing if it asks for all those informations
    name = 'Daniel Opitz'
    vorname = 'Daniel'
    nachname = 'Opitz'
    email = 'danielopitz91@gmail.com'
    tele = '+491738272304'
    strasse = 'Humboldstrasse'
    nr = '8'
    plz = '76131'
    ort = 'Karlsruhe'

class SPECS:
    rent_min = 500
    rent_max = 1000
    rent_total = 1300
    rooms_min = 2
    rooms_max = 4
    area_min = 55
    area_max = 85
    go_zones = ur'Waldstadt|Oststadt|Rintheim|Durlach|Hagsfeld|S[^\s]+dstadt|Nordweststadt|Nordstadt|Innenstadt-West|Innenstadt|Innenstadt-Ost'
    no_go_zones = ur"Gr[^\s]+tzingen|Bretten|Knielingen|Daxlanden|Gr[^\s]+nwinkel|R[^\s]+ppurr|Wolfartsweier|Gr[^\s]+nwettersbach|Stupferich|Palmbach|Hohenwettersbach|Ettlingen|Oberreut"

    #Replace this by the search you're intersted in (do a manual search and copy/paste URL)
    search_url = 'https://www.immobilienscout24.de/Suche/S-2/Wohnung-Miete/Umkreissuche/Karlsruhe/-/-114684/2124104/-/1276001019/5/2,00-/50,00-/EURO--750,00'

#Modify according to your needs ;)
contact_message = u"""Hallo,
mein Name is Daniel Opitz, bin 28 Jahre alt und suche eine Wohnung für mich und meine Freundin in Karlsruhe. 
Ihr Angebot passt dabei sehr gut auf meine Suchkriterien. Wir wünschen uns für unsere erste gemeinsame Wohnung etwas mehr Platz. 
Ich habe am KIT mein Informatikstudium abgeschlossen und arbeite seit August ebenfalls dort als wissenschaftlicher Mitarbeiter. 
Meine Freundin arbeitet als Steuerfachangestellte beim Steuerberater.
Wir sind beides nichtraucher und haben keine Haustiere.
Wir würden uns sehr über eine Rückmeldung freuen.

Mit Freundlichen Grüßen,
Daniel Opitz und Anna-Lena Wiedmann
"""

slack_url = None #if you have Slack, put a Webhook URL here and you will get notified if the bot finds something interesting.

#Here we will keep ads that we have visited already...
db_filename = 'scout.json'

def send_slack_message(text):
    payload = {'text' : text,'mrkdwn' : True}
    if slack_url is None:
        return
    try:
        response = requests.post(slack_url,data = {'payload' : json.dumps(payload)})
    except:
        print "Can't deliver message to Slack!"

def load_db():
    ads = []
    if not os.path.exists(db_filename):
        return []
    with open(db_filename,"r") as input_file:
        for line in input_file:
            ads.append(json.loads(line))
    return ads

def save_db(ads):
    with open(db_filename,"w") as output_file:
        for ad in ads:
            try:
                output_file.write(json.dumps(ad)+"\n")
            except:
                print "Could not write entry!"
                continue

# change the criteria here like max rooms etc.
def is_suitable(ad):
    # for a in ad:
    #     print a, ad[a]
    """
    This function determines if an ad is suitable or not. Modify according to your needs.
    """
    if not 'Ort' in ad or not 'Zimmer' in ad or not 'rent' in ad or not 'flaeche' in ad:
        #raw_input("nix von kriterien in ad")
        return False
    if ad['rent'] is not None:
        try:
            rent = int(ad['rent'])
            if rent > SPECS.rent_max or rent < SPECS.rent_min:
                print "zu teuer"
                #raw_input()
                return False
        except:
            #raw_input("rent ist non kp wieso")
            return None
    else:
        print "rent is none"
        #raw_input()
        return False

    try:
        gesamtmiete = ad['Gesamtmiete'].split(" ")[0]
        if int(gesamtmiete) > SPECS.rent_total:
            return False
    except:
        return None

    try:
        if int(ad['Zimmer']) < SPECS.rooms_min or int(ad['Zimmer']) > SPECS.rooms_max:
            print "Nicht genug Zimmer"
            #raw_input()
            return False
    except:
        #raw_input("zimmer ist none")
        return None
    try:
        if int(ad['flaeche']) < SPECS.area_min or int(ad['flaeche']) > SPECS.area_max:
            print "zu klein/gross"
            #raw_input()
            return False
    except:
        #raw_input("wohnflaeche ist none")
        return None
    exchange_regex = r"alleinerziehende|Zwischenmiete|WBS|Wohnberechtigungsschein|Wohnungstausch|Tauschangebot|Tausch"
    if re.search(exchange_regex,ad['description'],re.I) or \
       re.search(exchange_regex,ad['title'],re.I):
       print "kack titel"
       #raw_input()
       return False
    if re.search(r"\bsuche\b|\bsucht\b",ad['title'],re.I):
        print "sucht"
        #raw_input()
        return False
    if not (re.search(SPECS.go_zones,ad['Ort'],re.I) or re.search(SPECS.go_zones,ad['title'],re.I) or re.search(SPECS.go_zones,ad['description'],re.I) or re.search(SPECS.go_zones,ad['stadtteil'],re.I)):
        print "nicht wo wir hin wollen"
        #raw_input()
        return False
    if re.search(SPECS.no_go_zones,ad['Ort'],re.I) or re.search(SPECS.no_go_zones,ad['title'],re.I) or re.search(SPECS.no_go_zones,ad['description'],re.I) or re.search(SPECS.no_go_zones,ad['stadtteil'],re.I):
        print "no go zone"
        #raw_input()
        return False
    #raw_input("suitable!")
    return True


def notify_me_of(ad):
    my_ad = {}
    my_ad.update(ad)
    my_ad['description'] = "> "+ "\n> ".join(my_ad['description'].split("\n"))
    message =u"""
## Neues Angebot: %(title)s

%(url)s

Zimmer: **%(Zimmer)s**
Miete: **%(rent_str)s**
Ort: **%(Ort)s**

## Beschreibung

%(description)s

## Telefon

**%(phone)s**

""" % my_ad

    print message

    send_slack_message(message)



lines = contact_message.split(u"\n")
contact_message = u""

for line in lines:
    if not line.strip():
        contact_message+=u"\n\n"
    else:
        contact_message+=unicode(line.strip())+u" "

print contact_message

import time

last_ping = None

def contact(ad,browser):
    ad['contacted'] = True

    browser.find_element_by_xpath("//span[text()='Anbieter kontaktieren']").click()
    WebDriverWait(browser, 2).until(
            EC.presence_of_element_located((By.ID, "contactForm-Message"))
    )



    message_element = browser.find_element_by_xpath("//*[@id='contactForm-Message']")
    message_element.send_keys(Keys.CONTROL + "a")
    message_element.send_keys(contact_message)

    try:
        butt = browser.find_element_by_xpath("//button[@class='button-primary palm-one-whole']")
        butt.click()
    except:
        print "could not find 'anfrage senden' button"

    try:
        butt = browser.find_element_by_xpath("//span[contains(text(),'Weiter')]")
        Select(browser.find_element_by_id('contactForm-salutation')).select_by_value("MALE")
        browser.find_element_by_id("contactForm-firstName").send_keys(ME.vorname)
        browser.find_element_by_id("contactForm-lastName").send_keys(ME.nachname)
        browser.find_element_by_id("contactForm-emailAddress").send_keys(ME.email)
        browser.find_element_by_id("contactForm-phoneNumber").send_keys(ME.tele)
        browser.find_element_by_id("contactForm-street").send_keys(ME.strasse)
        browser.find_element_by_id("contactForm-houseNumber").send_keys(ME.nr)
        browser.find_element_by_id("contactForm-postcode").send_keys(ME.plz)
        browser.find_element_by_id("contactForm-city").send_keys(ME.ort)
        butt.click()
        WebDriverWait(browser, 2).until(
                EC.presence_of_element_located((By.ID, "contactForm-moveInDateType"))
        )
        Select(browser.find_element_by_id('contactForm-moveInDateType')).select_by_value("FLEXIBLE")

        Select(browser.find_element_by_id('contactForm-numberOfPersons')).select_by_value("TWO_PERSON")
        Select(browser.find_element_by_id('contactForm-employmentRelationship')).select_by_value("STUDENT")
        Select(browser.find_element_by_id('contactForm-income')).select_by_value("OVER_2000_UPTO_3000")
        butt = browser.find_element_by_xpath("//button[contains(text(),'Anfrage senden')]")
        butt.click()
        WebDriverWait(browser,3).until(
        EC.presence_of_element_located(By.XPATH,"//h2[contains(text(),'Nachricht')]")
        )

    except:
        print "could not find 'weiter' button"


def get_attributes(browser):
    attribute_lists = browser.find_elements_by_xpath('//div[contains(@class,"is24-ex-details")]')
    attributes = {}
    for attribute_list in attribute_lists:
        current_name = None
        for item in attribute_list.find_elements_by_xpath('.//dd | .//dt'):
            if item.tag_name == 'dt':
                current_name = item.text.strip()
                if not current_name:
                    continue
                if current_name[-1] == ':':
                    current_name = current_name[:-1]
            elif current_name is not None:
                attributes[current_name] = item.text.strip()
    attributes['Ort'] = browser.find_element_by_xpath("//*[@class='zip-region-and-country']").text
    attributes['Zimmer'] = float(attributes['Zimmer'].replace(',', '.'))
    flaeche_str  = browser.find_element_by_xpath("//*[@class='is24qa-flaeche is24-value font-semibold']").text
    rent_str = browser.find_element_by_xpath('//*[@class="is24qa-kaltmiete is24-value font-semibold"]').text

    attributes['rent_str'] = rent_str

    try:
        attributes['rent'] = re.match(r".*?(\d+)\s*",rent_str).group(1)
    except:
        attributes['rent'] = None

    attributes['flaeche'] = re.match(r".*?(\d+)\s*",flaeche_str).group(1)

    attributes['title'] = browser.find_element_by_id('expose-title').text

    phone_number = browser.find_elements_by_xpath('//*[contains(@class,"phoneline-number")]')

    if len(phone_number):
        attributes['phone'] = phone_number[0].text
    else:
        attributes['phone'] = ''
    try:
        p_text = browser.find_element_by_xpath('//pre[@class="is24qa-objektbeschreibung"]')
        desc = p_text.text


        try:
            lage = browser.find_element_by_class_name('//pre[@class="is24qa-lage"]')
            desc += " "+lage.text

        except:
            pass
    except:
        desc = ""
    attributes['description'] = desc

    link_chain = browser.find_elements_by_xpath("//div[@id='is24-main']//div[@class='palm--flex__order--1 flex-item--center']//a")

    attributes['stadtteil'] = link_chain[3].text
    return attributes



def check_ads(ads_by_id):

    browser = webdriver.Firefox()
    browser.set_page_load_timeout(60)
    browser.set_window_position(-1000, 0)

    try:
        browser.delete_all_cookies()

        if True:
            browser.get('https://sso.immobilienscout24.de/sso/login?appName=is24main&source=meinkontodropdown-login&sso_return=https://www.immobilienscout24.de/sso/login.go?source%3Dmeinkontodropdown-login%26returnUrl%3D/geschlossenerbereich/start.html?source%253Dmeinkontodropdown-login')
            browser.find_element_by_id('j_username').send_keys(LOGIN.email)
            browser.find_element_by_id('j_password').send_keys(LOGIN.password)
            browser.find_element_by_xpath("//button[@id='registration.submit']").click()

        browser.get(SPECS.search_url)

        result_list = browser.find_element_by_id('resultListItems')
        result_items = result_list.find_elements_by_xpath(".//li[@class='result-list__listing ']")
        links = {}
        for result_item in result_items:
            link = result_item.find_element_by_xpath(".//a[@class='result-list-entry__brand-title-container']")
            links[link.get_attribute('href')] = link.text


        try:
            for link_href,link_text in links.items():
                print "="*20
                o = urlparse.urlparse(link_href)
                ad_number = re.match(r".*\/([\d\w\-]+)$",o.path)
                if not ad_number:
                    print "Cannot find ad number"
                    continue
                ad_id = ad_number.group(1)
                #print ad_id
                print link_href
                browser.get(link_href)

                try:
                    element = WebDriverWait(browser, 10).until(
                            EC.presence_of_element_located((By.ID, "is24-expose-contact-bar-bottom"))
                        )
                    print "Found it"
                except TimeoutException:
                    print "Timeout!"
                    continue

                attributes = get_attributes(browser)
                attributes['id'] = ad_id
                attributes['url'] = link_href

                ad_number = attributes['id']

                new_ad = False
                if ad_number in ads_by_id:
                    print "Updating ad."
                    ads_by_id[ad_number].update(attributes)
                else:
                    print "New ad!"
                    new_ad = True
                    ads_by_id[ad_number] = attributes
                print ads_by_id[ad_number]['title']
                print ads_by_id[ad_number]['stadtteil']
                print "Suitable:",is_suitable(ads_by_id[ad_number])
                if not new_ad:
                    continue

                ad = ads_by_id[ad_number]
                ad['suitable'] = is_suitable(ad)
                if ad['suitable']:
                    if 'contacted' not in ad or ad['contacted'] is False:
                        print "Not yet contacted!"
                        if not ad['phone']:
                            contact(ad,browser)
                        else:
                            send_slack_message("Bitte selbst anrufen: %s (%s - %s)" % (ad['phone'],ad['title'],ad['url']) )
                        notify_me_of(ad)
                else:
                    send_slack_message("Nicht geeignet: %s (%s)" % (ad['title'],ad['url']))
                pprint.pprint(ads_by_id[ad_number])

                print "\n\n\n"


        except KeyboardInterrupt:
            print "CTRL-C pressed, aborting..."
            raise
    finally:

        browser.quit()

if __name__ == '__main__':
    ads = load_db()
    print "Loaded %d entries" % len(ads)

    ads_by_id = {}

    for ad in ads:
        if 'id' in ad:
            ads_by_id[ad['id']] = ad

    while True:

        if last_ping is None or time.time()-last_ping > 60*60:
            last_ping = time.time()
            send_slack_message("Indexed %d ads so far, found %d suitable ones." % (len(ads_by_id),len([ad for ad in ads_by_id.values() if 'suitable' in ad and ad['suitable']])))
        try:
            check_ads(ads_by_id)
        except KeyboardInterrupt:
            save_db(ads_by_id.values())
            break
        except:
            print "An exception occured..."
            print traceback.format_exc()
            send_slack_message("Exception: %s" % traceback.format_exc())
        print "Waiting 30 secs..."
        save_db(ads_by_id.values())
        time.sleep(30)
