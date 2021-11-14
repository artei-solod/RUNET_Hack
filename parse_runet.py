import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html

import os
import pandas as pd
import numpy as np 
import uuid
import json

import pickle
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import os
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from time import sleep
pd.set_option('display.max_columns', None)
from selenium.webdriver.common.action_chains import ActionChains
import re
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import torch
from transformers import AutoModelForSequenceClassification
from transformers import BertTokenizerFast
import platform
from selenium.webdriver.chrome.options import Options
chrome_options = Options()
chrome_options.add_argument("--headless")
class SiteRatingExtractor:
    
    def __init__(self):
        self.tokenizer = BertTokenizerFast.from_pretrained('blanchefort/rubert-base-cased-sentiment')
        self.model = AutoModelForSequenceClassification.from_pretrained('blanchefort/rubert-base-cased-sentiment', return_dict=True)
    
    def get_estimate(self, name):
        result = {}
        result['pr'], result['iks'] = self.get_rating(name)
        result['google_titles'], result['google_subtitles'] = self.get_google_titles_subtitles(name)
        result['yandex_news_headers'] = self.get_news_headers(name)
        result['yandex_reviews'] = self.get_reviews_yandex(name)
        
        res = float(result['pr']) + float(result['iks'])/100 + self.predict_sentiment(result['google_titles']) + \
            self.predict_sentiment(result['google_subtitles']) + self.predict_sentiment(result['yandex_news_headers']) + \
                self.predict_sentiment(result['yandex_reviews']['reviews']) + self.predict_sentiment(result['yandex_reviews']['tags']) + \
                    (float(str(result['yandex_reviews']['mark']).replace(',','.')) - 3.5) * 10
        
        return [res, result]
        
    def get_rating(self, name):
        name = name + ' официальный сайт'
        with webdriver.Chrome(ChromeDriverManager().install(),options=chrome_options) as driver:
            driver.get('https://yandex.ru/search/?text=' + name.replace(' ','+'))
            sleep(2)
            html = driver.page_source
            #link = html.split('Ссылка на сайт организации:')[1].split('"')[0]
            link = html.split('tabindex="0" target=')[1].split('<b>')[1].split('</b>')[0]
        link = '.'.join(link.split('.')[-2:]).replace('https://', '').replace('http://','').replace('/','')

        with webdriver.Chrome(ChromeDriverManager().install(),options=chrome_options) as driver:
            driver.get('https://pr-cy.ru/counter/')
            sleep(2)
            elem = driver.find_elements_by_class_name('form-control')
            elem[0].send_keys(link)
            sleep(1)
            elem[0].send_keys(Keys.ENTER)
            sleep(1)
            pic = requests.get('http://s.pr-cy.ru/counters/' + link).content
            with open('temp.png', 'wb') as handler:
                handler.write(pic)
        im = Image.open("temp.png")
        if platform.system() == 'Windows':
            pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'#os.path.join('C:','Program Files','Tesseract-OCR','tesseract.exe')
        text = pytesseract.image_to_string(im)
        try:
            rating = int(text.split()[1])
        except:
            rating = 0
        IKS = 0
#         with webdriver.Chrome(ChromeDriverManager().install()) as driver:
#             driver.get('https://a.pr-cy.ru/tools/check-sqi/')
#             sleep(2)
#             elem = driver.find_element_by_name('domains')
#             elem.send_keys(link)
#             sleep(1)
#             enter = driver.find_element_by_xpath('/html/body/div[2]/div[1]/div[3]/div[1]/div/form/div[2]/span/button')
#             sleep(1)
#             enter.click()
#             sleep(1)
#             rank_field = driver.find_element_by_class_name('ng-binding')
#             IKS = rank_field.text
#             m = False
       
            
            
        return [rating, IKS]
    
    def get_google_titles_subtitles(self, name):
        with webdriver.Chrome(ChromeDriverManager().install(),options=chrome_options) as driver:
            driver.get('https://google.com')
            elem = driver.find_element_by_css_selector('.gLFyf')
            elem.send_keys(name)
            sleep(2)
            elem.send_keys(Keys.ENTER)
            sleep(3)
            elem = driver.find_element_by_xpath("//*[contains(text(), 'Новости')]")
            elem.click()
            sleep(2)
            try:
                titles = [driver.find_element_by_xpath(f'/html/body/div[7]/div/div[9]/div[1]/div/div[2]/div[2]/div/div/div[{i}]/g-card/div/div/a/div/div[2]/div[2]').text.replace('\n', ' ').replace('...', '') for i in range(1,8)]
            except:
                titles = []
            try:
                subtitles = [driver.find_element_by_xpath(f'/html/body/div[7]/div/div[9]/div[1]/div/div[2]/div[2]/div/div/div[{i}]/g-card/div/div/a/div/div/div[3]').text.replace('\n', ' ').replace('...', '') for i in range(1,8)]
            except:
                subtitles = []
        return [titles, subtitles]
    
    def get_news_headers(self, name):
        with webdriver.Chrome(ChromeDriverManager().install(),options=chrome_options) as driver:
            driver.get('https://newssearch.yandex.ru/news/search?text=' + name.replace(' ', '+'))
            html = driver.page_source
            headers = [x for x in [x.split('"text">')[1].split('<')[0] for x in html.split('mg-snippet__url')[1:]] if len(x) >0]
        return headers
    
    def get_reviews_yandex(self, name):
        with webdriver.Chrome(ChromeDriverManager().install(),options=chrome_options) as driver:
            result = {}
            result['tags'] = []
            result['reviews'] = []
            driver.get('https://yandex.ru')
            elem = driver.find_elements_by_id('text')
            if len(elem) > 0:
                elem[0].send_keys(name)
            elem = driver.find_elements_by_class_name('search2__button')
            sleep(1)
            if len(elem) > 0:
                elem[0].click()
            sleep(3)
            elem = driver.find_elements_by_css_selector('span.Link_pseudo:nth-child(1)')
            if len(elem) > 0:
                elem[0].click()
            sleep(3)
            html = driver.page_source
            tags = [x.split('<')[0] for x in html.split('class="Button2-Text">')[1:-1]]
            if 'Оставить отзыв' in tags:
                tags = tags[tags.index('Оставить отзыв') + 1:]
            if 'Оставить отзыв' in tags:
                tags = tags[tags.index('Оставить отзыв') + 1:]
            result['tags'] = [x for x in tags if len(x) > 0][:10]
            reviews = [''.join([x.split('>')[1] for x in x.split('<')[1::2] if len(x.split('>')) > 1 and len(x.split('>')[1]) > 0]) for x in html.split('Cut TextCut')[1:-1]]
            result['reviews'] = [re.sub('{.+?}', '', x).split('Читать все отзывы')[0].split('Скрыть')[0] for x in reviews]
            try:
                result['mark'] = [x.split()[0].strip() for x in html.split('aria-label="Рейтинг: ')[1:]][0]
            except:
                result['mark'] = 3.5
            return result
        
    @torch.no_grad()    
    def predict_sentiment(self, text):
        try:
            inputs = self.tokenizer(text, max_length=512, padding=True, truncation=True, return_tensors='pt')
            outputs = self.model(**inputs)
            predicted = torch.nn.functional.softmax(outputs.logits, dim=1)
            pos = predicted.numpy()[:,1]*10
            neg = predicted.numpy()[:,2]*10
        except:
            pos = 0
            neg = 0
        return np.sum(pos - neg)


ext = SiteRatingExtractor()
    
app = dash.Dash(__name__, url_base_pathname='/')
   
def serve_layout():
    session_id = str(uuid.uuid4())
    return html.Div(children=[
        
        html.Label('Введите данные о заявках:'), html.Br(), html.Br(),
        dcc.Input( id="data_input", value='', type='text', style={'width': '90%', 'height': '40px'}),
        html.Button(id='submit_button', n_clicks=0, children='Проверить', style={'height': '40px'}),
        html.Div(id = "data_output")
    ])
       

@app.callback(Output('data_output', 'children'),
              State('data_input', 'value'),
              Input('submit_button', 'n_clicks') )
def read_value(value, n_clicks):
    if len(value)>0:
        value, _ = ext.get_estimate(value)
        return html.Div([
            "Рейтинг: " + str(value) + "",
        ])
    else:
        return ""


    
    
if __name__ == '__main__':
    app.layout = serve_layout
    app.index_string = '''<!DOCTYPE html>
<html>
<head>
<title> Премия Рунета </title>
{%metas%}

    {%favicon%}
    {%css%}
<style>

#page {
    width: 100%;
    background-color: #dddddd;
    color: #191970;
}
#header {
    margin: 0 0 0 0;
    background-color:black;
    text-align:center;
    font-size: 26px;
    line-height: 100px;
    font-family: Verdana, Geneva, sans-serif;
    letter-spacing: 2 px;
}
@-webkit-keyframes pulsate {
 50% { color: #FFD700; text-shadow: 0 -1px rgba(0,0,0,.3), 0 0 5px #FEFE22, 0 0 8px #F8F32B; }
}
@keyframes pulsate {
 50% { color: #FFD700; text-shadow: 0 -1px rgba(0,0,0,.3), 0 0 5px #FEFE22, 0 0 8px #F8F32B; }
}
#blink7 {
  color: #F8F32B;
  text-shadow: 0 -1px rgba(0,0,0,.1);
  background: black;
  -webkit-animation: pulsate 1.2s linear infinite;
  animation: pulsate 1.2s linear infinite;
}
#top-menu {width:1500px; height:74px; }
.bg-1 {width:1340px; height:64px; background:black repeat-x; padding:0 0 0 10px;}
.bg-2 {width:1350px; height:8px; background:#FFD700; margin:1 auto;}
.bg-1 ul {margin:0; padding:0; list-style:none;}
.bg-1 ul li {float:left; background:url(images/m2.png) no-repeat right center; padding:0 30px 0 0;}
.bg-1 ul li a {display:block; height:40px; padding:24px 40px 0 40px; color:#FFD700; text-decoration:none; text-transform:uppercase;}
.bg-1 ul li a:hover {color:black; background:#FFD700;}#sidebar>ul {
    list-style: none;
    padding:5px;
}
#logo {
    width: 5px;
    height: 5px;
    margin: 1;
    padding: 10px;
}
#content {
    background-color:#fff;
    
    width:70%;
    margin: 0 auto; 
    text-align: left;
    float:center;
    padding:5px;    
}
#footer {
    background-color:#FFD700;
    clear:both;
    text-align:center;
    padding:5px;   
    width: 100%;
}
</style>
</head>
<body>
<div id="header">
<div id="logo">
        <img src="original.png" alt="logo" width="80px" height="100px">
</div>
        <h1 id="blink7"> Алгоритм поиска победителя</h1>

</div>

<div id="content">
<p>Данный сайт предназначен для определения победителей Премии Рунета.</p>
{%app_entry%}
</div>
	
<div id="footer">
Copyright © 2021
</div>
<footer>
{%config%}
{%scripts%}
{%renderer%}
</footer>
</body>
    '''

   
    app.run_server(debug=False, host="0.0.0.0", port=8000)

    print("stopping...")


