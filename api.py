import os,json,urllib2,smtplib,email,tempfile,hashlib,errno
import flask,werkzeug

app = flask.Blueprint("api", __name__)

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            app.logger.exception("mkdir_p(%s)" % path)
            raise

def get_json_from_cms(url, throw_404=True):
    try:
        return json.load(urllib2.urlopen(flask.current_app.config["CMS_BASE"] + "/" + url))
    except urllib2.HTTPError, e:
        if e.code == 404:
            if throw_404: raise werkzeug.exceptions.NotFound()
            else: return None
        #else
        raise

    except urllib2.URLError, e:
        raise werkzeug.exceptions.ServiceUnavailable(e)

@app.route("/", methods=["GET"])
def info():
    mailfrom = flask.current_app.config.get("GMAIL_ID")
    password = flask.current_app.config.get("GMAIL_PASSWORD")
    print mailfrom, password
    return "API"

@app.route("/send_download_link",methods=['POST','PUT'])
def send_download_link():
    mailfrom = flask.current_app.config.get("GMAIL_ID")
    password = flask.current_app.config.get("GMAIL_PASSWORD")

    if not mailfrom or not password:
        return flask.jsonify({"success":False, "info":"NOCONFIG"})

    mailto = flask.request.json.get("email")
    charset = "ISO-2022-JP"
    body = flask.render_template("send_download_link_body.txt")
    subject = flask.render_template("send_download_link_subject.txt")
    msg = email.MIMEText.MIMEText(body.encode(charset), "plain", charset)
    msg["Subject"] = email.Header.Header(subject, charset)
    msg["From"] = mailfrom
    msg["To"] = mailto
    msg["Date"] = email.Utils.formatdate(localtime=True)

    h = hashlib.new("md5")
    h.update(mailto)
    email_hash = h.hexdigest()

    email_log_dir = os.path.join(tempfile.gettempdir(), "walbrixnet-sendemail")
    email_log_file = os.path.join(email_log_dir, email_hash)

    try:
        if os.path.isfile(email_log_file):
            email_log_stat = os.stat(email_log_file)
            if email_log_stat.st_mtime > time.time() - 60:
                return flask.jsonify({"success":False, "info":"ALREADYSENT"})

        mkdir_p(email_log_dir)
        smtp = smtplib.SMTP("smtp.gmail.com", 587)
        try:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(mailfrom, password)
            smtp.sendmail(mailfrom, [mailto], msg.as_string())
            with open(email_log_file, "w") as f:
                f.write(mailto + "\n")
                f.write(body.encode("utf-8"))
        finally:
            smtp.close()
    except Exception, e:
        flask.current_app.logger.exception("send_download_link")
        return flask.jsonify({"success":False, "info":e.message})

    return flask.jsonify({"success":True,"info":mailto})

@app.route("/walbrix-latest-jp-DVD.iso")
def redirect_to_fast_download():
    page_data = get_json_from_cms("download.json")    
    return flask.redirect("http://dist.walbrix.net/walbrix-%s-jp-DVD.iso" % page_data["version"])
