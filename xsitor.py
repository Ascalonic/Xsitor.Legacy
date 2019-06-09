from flask import Flask, render_template, request, make_response
from bs4 import BeautifulSoup
from operator import itemgetter
import mysql.connector
import requests
import time

app = Flask(__name__)

def getMySqlConnection():
    mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="Fucksenseai#1",
            database="xsitor"
    )
    return mydb

def logSearch(query, ip):
    mydb = getMySqlConnection()
    mycursor = mydb.cursor()

    sql = "INSERT INTO SearchHistory (ipaddr, query, timestamp) VALUES (%s, %s, %s)"
    val = (ip, query, time.strftime('%Y-%m-%d %H:%M:%S'))
    mycursor.execute(sql, val)

    mydb.commit()
    mycursor.close()
    mydb.close()

def logError(msg, ip):
    mydb = getMySqlConnection()
    mycursor = mydb.cursor()

    sql = "INSERT INTO ErrorLog (message, ipaddr, timestamp) VALUES (%s, %s, %s)"
    val = (msg, ip, time.strftime('%Y-%m-%d %H:%M:%S'))
    mycursor.execute(sql, val)

    mydb.commit()
    mycursor.close()
    mydb.close()

def setSecurityHeaders(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    #response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['server'] = 'Ascalonic'

    return response

@app.route("/")
def mainpage():

    query = request.args.get('q')

    logSearch(query, request.remote_addr)

    if query!=None:
        full_res = getPornhubResults(query) + getXvideosResults(query)
        full_res = sorted(full_res, key=itemgetter('score'), reverse=True)

        response = make_response(render_template('index.html', results = full_res))
        response = setSecurityHeaders(response)        

        return(response)
    else:
        response = make_response(render_template('index.html'))
        response = setSecurityHeaders(response)
        return(response)

@app.route("/google904fa31d51def8dc.html")
def google_verif():
    return("google-site-verification: google904fa31d51def8dc.html")

@app.route("/xvdown", methods=['POST'])
def getXvideosDownload():
    vidurl = request.form.get('vidurl')
    quality = request.form.get('quality')
    page = requests.get(vidurl)
    contents = page.content

    if quality=='low':
        url_finder = "html5player.setVideoUrlLow(\'"
    else:
        url_finder = "html5player.setVideoUrlHigh(\'"

    url_start = contents.find(url_finder) + len(url_finder)
    url = contents[url_start:]
    url_end = url.find("\'")
    url = url[0:url_end]

    return(url)

@app.route("/phdown", methods=['POST'])
def getPornhubDownload():
    vidurl = request.form.get('vidurl')
    page = requests.get(vidurl)
    contents = page.content
    url_finder = 'videoUrl":"'
    url_start = contents.find(url_finder) + len(url_finder)
    url = contents[url_start:]
    url_end = url.find('"')
    url = url[0:url_end]
    url = url.replace('\\', '')

    return(url)

def getXvideosResults(query):
    page = requests.get('https://www.xvideos.com/?k=' + query.replace(' ', '+'))
    contents = page.content
    soup = BeautifulSoup(contents, 'html.parser')
    xv_res = soup.findAll("div", {"class": "thumb-block "})
    
    results = []
    maxviews = 0

    for res in xv_res:
        result = dict()
        try:
            thumb_src = res.find("img")['data-src']
        except:
            continue

        link = res.find("a")['href']
        para = res.find("p")
        title = para.find("a")['title']

        duration = res.findAll("span", {"class":"duration"})[0].encode_contents()

        try:
            span_bg = res.findAll("span", {"class":"bg"})[0]
            views = span_bg.findAll("span")[1].encode_contents()
            views = views.replace(' ', '')
            views = views.replace('-', '')
        except:
            span_md = res.findAll("p", {"class":"metadata"})[0]
            views = span_md.getText().splitlines()[1]

        views = views.replace('Views', '')

        multiple = 1
        if 'k' in views:
            views = views.replace('k', '')
            multiple = 1000
        elif 'M' in views:
            views = views.replace('M', '')
            multiple = 1000000

        views = float(views) * multiple

        if views>maxviews:
            maxviews = views

        result['source'] = 'xvideos'
        result['link'] = 'https://xvideos.com' + link
        result['thumb'] = thumb_src
        result['title'] = title
        result['views'] = views
        result['duration'] = duration

        #THUMBNUM fix for thumbnail
        if 'THUMBNUM' in result['thumb']:
            result['thumb'] = result['thumb'].replace('THUMBNUM', '27')
            result['thumb'] = result['thumb'].replace('thumbs169', 'thumbs169l')

        results.append(result)

    for res in results:
        res['score'] = 0.6 + 0.35 * float(res['views'])/maxviews

    return results

def getPornhubResults(query):
    results = []
    
    page = requests.get('https://www.pornhub.com/video/search?search=' + query.replace(' ', '+'))
    contents = page.content
    soup = BeautifulSoup(contents, 'html.parser')
    
    try:
        ph_res_root = soup.findAll("ul", {"class": "videos search-video-thumbs"})[0]
        ph_res = ph_res_root.findAll("li", {"class": "js-pop videoblock videoBox"})

        for res in ph_res:
            result = dict()
            wrap = res.findAll("div", {"class": "wrap"})[0]
            phimage = wrap.findAll("div", {"class": "phimage"})[0]

            try:
                elem_img = phimage.findAll("div", {"class":"img fade fadeUp videoPreviewBg"})[0]
            except:
                elem_img = phimage.findAll("div", {"class":"img fade fadeUp"})[0]

            main_a = elem_img.find("a")
            link = main_a['href']
            title = main_a['title']
            th_info = main_a.find("img")
            thumb_src = th_info['data-mediumthumb']
            duration = res.findAll("var", {"class":"duration"})[0].encode_contents()
        
            #rank the result
            rating_cont = res.findAll("div", {"class": "rating-container up"})[0]
            rating_elem = rating_cont.findAll("div", {"class":"value"})[0]
            perc = rating_elem.encode_contents()
            perc = perc.replace('%', '')
            score = float(perc)/100

            result['source'] = 'pornhub'
            result['link'] = 'https://pornhub.com' + link
            result['thumb'] = thumb_src
            result['duration'] = duration
            result['title'] = title
            result['score'] = score

            results.append(result)
    except Exception as e:
        logError('PHRES (' + query + '):' + str(e), request.remote_addr)

    return results

if __name__ == "__main__":
    app.run(host='0.0.0.0')
