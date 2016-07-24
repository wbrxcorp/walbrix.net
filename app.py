#!/usr/bin/python
# -*- coding:utf-8 -*-
# emerge markdown (< 2.5)
# https://github.com/dart-lang/py-gfm

import os,json,re,urllib2,datetime
import flask,werkzeug,markdown,feedgenerator,pytz
import MySQLdb

app = flask.Flask(__name__)
app.config.from_pyfile('default_config.py')
app.config.from_pyfile('local_config.py', silent=True)

try:
    import api
    app.register_blueprint(api.app, url_prefix="/api")
except ImportError:
    pass

timezone = pytz.timezone("Asia/Tokyo")

# http://detectmobilebrowsers.com/
reg_b = re.compile(r"(android|bb\\d+|meego).+mobile|avantgo|bada\\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|mobile.+firefox|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\\.(browser|link)|vodafone|wap|windows ce|xda|xiino", re.I|re.M)
reg_v = re.compile(r"1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\\-(n|u)|c55\\/|capi|ccwa|cdm\\-|cell|chtm|cldc|cmd\\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\\-s|devi|dica|dmob|do(c|p)o|ds(12|\\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\\-|_)|g1 u|g560|gene|gf\\-5|g\\-mo|go(\\.w|od)|gr(ad|un)|haie|hcit|hd\\-(m|p|t)|hei\\-|hi(pt|ta)|hp( i|ip)|hs\\-c|ht(c(\\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\\-(20|go|ma)|i230|iac( |\\-|\\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\\/)|klon|kpt |kwc\\-|kyo(c|k)|le(no|xi)|lg( g|\\/(k|l|u)|50|54|\\-[a-w])|libw|lynx|m1\\-w|m3ga|m50\\/|ma(te|ui|xo)|mc(01|21|ca)|m\\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\\-2|po(ck|rt|se)|prox|psio|pt\\-g|qa\\-a|qc(07|12|21|32|60|\\-[2-7]|i\\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\\-|oo|p\\-)|sdk\\/|se(c(\\-|0|1)|47|mc|nd|ri)|sgh\\-|shar|sie(\\-|m)|sk\\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\\-|v\\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\\-|tdg\\-|tel(i|m)|tim\\-|t\\-mo|to(pl|sh)|ts(70|m\\-|m3|m5)|tx\\-9|up(\\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\\-|your|zeto|zte\\-", re.I|re.M)

def is_mobile():
    user_agent = flask.request.headers.get('User-Agent')
    if reg_b.search(user_agent): return True
    if reg_v.search(user_agent[0:4]): return True
    return False

def is_html5_compliant_browser():
    user_agent = flask.request.headers.get('User-Agent')
    if not user_agent: return False
    ie_version = re.search(r'MSIE ([0-9]+)', user_agent)
    if not ie_version: return True
    try:
        ie_version = int(ie_version.groups(0)[0])
    except ValueError:
        return False
    return ie_version >= 9

@app.context_processor
def inject_env():
    return {
        "is_mobile":is_mobile(),
        "is_html5_compliant":is_html5_compliant_browser()
    }

def parse_datetime(t):
    if isinstance(t, datetime.datetime): return t
    return datetime.datetime.fromtimestamp(t / 1000) if isinstance(t, (int,long)) else datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ")

@app.template_filter("datetime")
def _datetime(t):
    return parse_datetime(t).strftime(u"%Y-%m-%d %H:%M")

@app.template_filter("date")
def _date(t):
    t = parse_datetime(t)
    return u"%d年%d月%d日" % (t.year, t.month, t.day)

def check_referer(referer):
    referer_spam_blacklist = [
        r'https?:\/\/(.+\.)?buttons-for-website\.com(/.*)?$',
        r'https?:\/\/(.+\.)?7makemoneyonline\.com(/.*)?$',
        r'https?:\/\/(.+\.)?semalt\.com(/.*)?$'
    ]
    for spam in referer_spam_blacklist:
        if re.match(spam, referer):
            flask.abort(403)

@app.before_request
def before_request():
    referer = flask.request.referrer
    if referer: check_referer(referer)
    flask.g.db = MySQLdb.connect(
        host=app.config["MYSQL_HOST"],db=app.config["MYSQL_DATABASE"],
        user=app.config["MYSQL_USER"],passwd=app.config["MYSQL_PASSWORD"],
        charset='utf8', use_unicode=True
    )

@app.teardown_request
def teardown_request(exception=None):
    flask.g.db.close()

@app.route('/favicon.ico')
def favicon():
    return flask.send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/robots.txt')
def robots():
    return flask.send_from_directory(os.path.join(base_dir, 'static'),
                               'robots.txt', mimetype='text/plain')

@app.route('/no_report')
def no_report():
    response = flask.make_response("OK")
    response.set_cookie("no_report", "1", expires="Tue, 1-Jan-2030 00:00:00 GMT", max_age=86400*365*20)
    return response

def get_json_from_cms(url, throw_404=True):
    try:
        return json.load(urllib2.urlopen(app.config["CMS_BASE"] + "/" + url))
    except urllib2.HTTPError, e:
        if e.code == 404:
            if throw_404: raise werkzeug.exceptions.NotFound()
            else: return None
        #else
        raise

    except urllib2.URLError, e:
        raise werkzeug.exceptions.ServiceUnavailable(e)

def generate_prefix_from_path(path):
    return re.sub(r"\/\/+", "/", app.config["ROOT_PREFIX"] + ('/' + path if path else ''))

def get_prefix_data(cur, prefix):
    # プレフィクスデータの読み込み
    data = {"prefix":prefix}
    prefix_components = prefix.split('/')
    for i in range(0, len(prefix_components) + 1):
        cur.execute("select data from prefixes where prefix=%s", ('/'.join(prefix_components[:i]),))
        row = cur.fetchone()
        if row: data.update(json.loads(row[0]))
    return data

def get_directory(path, labels, page_length = 20):
    prefix = generate_prefix_from_path(path)
    cur = flask.g.db.cursor()
    data = get_prefix_data(cur, prefix)

    entries = []
    label_condition = ""
    if isinstance(labels, list):
        if len(labels) > 0:
            label_condition = "and label in (%s)" % ','.join(["%s"] * len(labels))
        else:
            label_condition = "and label is null"

    cur.execute("select name,title,description,page_image,format,published_at,label from entries left outer join entries_labels on entries.id=entries_labels.entry_id where prefix=%s and visible and published_at is not null and published_at<=now() " + label_condition + " order by published_at desc limit %s offset %s", tuple([prefix] + (labels if (labels is not None and len(labels) > 0) else []) + [page_length, 0]))

    row = cur.fetchone()
    while row is not None:
        name = row[0]
        if len(entries) == 0 or entries[-1]["name"] != name:
            entries.append({
                "name":name,
                "title":row[1],
                "description":row[2],
                "page_image":row[3],
                "format":row[4],
                "published_at":row[5],
                "labels":[row[6]] if row[6] is not None else []
            })
            #print row[5]
        elif row[6] is not None:
            entries[-1]["labels"].append(row[6])
        row = cur.fetchone()

    data["entries"] = entries

    return data

def get_page(path, name, throw_404=True):
    prefix = generate_prefix_from_path(path)
    cur = flask.g.db.cursor()

    data = get_prefix_data(cur, prefix)

    cur.execute("select title,description,page_image,content,data,format,label from entries left outer join entries_labels on entries.id=entries_labels.entry_id where prefix=%s and name=%s and visible", (prefix, name))
    row = cur.fetchone()
    if row is None:
        if throw_404: flask.abort(404)
        else: return None

    data.update({
        "name":name,
        "title":row[0],
        "description":row[1],
        "page_image":row[2],
        "content":row[3],
        "format":row[5],
        "labels":[row[6]] if row[6] is not None else []
    })
    if row[4] is not None: data.update(json.loads(row[4]))

    # ラベル拾う
    row = cur.fetchone()
    while row is not None:
        data["labels"].append(row[6])
        row = cur.fetchone()

    return data

@app.route('/<page_name>.html')
def page(page_name):
    return page_with_path("",page_name)

@app.route('/<path:path>/index.xml')
def rss(path):
    page_length = 100

    data = get_json_from_cms("%s/?limit=%d" % (path,page_length))
    entries = data["entries"]

    link = "%s%s/" % (flask.request.url_root,path)
    title = data["feed_title"] if "feed_title" in data else link
    description = data["feed_description"] if "feed_description" in data else link
    lang = data["lang"] if "lang" in data else "ja"

    feed = feedgenerator.Rss201rev2Feed(title=title,link=link,feed_url=flask.request.base_url,description=description,language=lang)
    for entry in entries[:50]:
        date = datetime.datetime.fromtimestamp(entry["published_at"] / 1000)
        link = "%s%s/%s.html" % (flask.request.url_root,path, entry["name"])
        feed.add_item(title=entry["title"],link=link, description=entry["description"] if "description" in entry else None,pubdate=datetime.datetime(date.year,date.month,date.day,0,0,0,0,timezone),unique_id=link)
    response = flask.make_response(feed.writeString('utf-8'))
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route('/<path:path>/<page_name>.html')
def page_with_path(path,page_name):
    if path.startswith("static"):
        return flask.send_from_directory(os.path.join(app.root_path, path), "%s.html" % page_name)

    if path.startswith("templates"): return "Not found", 404
    #entry = get_json_from_cms("%s/%s.json" % (path,page_name))
    entry = get_page(path, page_name)

    page_length = entry["page_length"] if "page_length" in entry else 20
    # 同一プレフィクスのエントリ一覧も
    #entry["entries"] = get_json_from_cms("%s/?limit=%d" % (path,page_length))["entries"]
    entry["entries"] = get_directory(path, None, page_length)["entries"]

    # 同一ラベルのエントリ一覧も
    if "labels" in entry and len(entry["labels"]) > 0:
        #entry["labeled_entries"] = get_json_from_cms("%s/?label=%s&limit=%s" % (path, entry["labels"][0],page_length))["entries"]
        entry["labeled_entries"] = get_directory(path, entry["labels"],page_length)["entries"]

    if "previous" in entry:
        #entry["previous"] = get_json_from_cms("%s/%s.json" % (path,entry["previous"]), False)
        entry["previous"] = get_page(path, entry["previous"], False)

    if "next" in entry:
        #entry["next"] = get_json_from_cms("%s/%s.json" % (path,entry["next"]), False)
        entry["next"] = get_page(path, path,entry["next"], False)

    if entry.get("apply_jinja2"):
        entry["content"] = flask.render_template_string(entry["content"], **entry)
    if entry.get("format") == "markdown":
        entry["content"] = markdown.markdown(entry["content"], extensions=['gfm'])

    return flask.render_template(entry["template"],**entry)

@app.route('/')
def index():
    return page("index")

@app.route('/<path:path>/')
def index_with_path(path):
    return page_with_path(path,"index")

@app.route('/<path:path>/<filename>')
def send_file(path,filename):
    if path.startswith("templates"): return "Not found", 404
    return flask.send_from_directory(os.path.join(app.root_path, path), filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)
