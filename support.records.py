#!/usr/bin/python

import commands
import re
import shutil
import datetime
import csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.message import Message
from email import encoders
from email.utils import COMMASPACE
import mimetypes

completeTotalCalls = 0
completeTotalDuration = 0
avgTalkTime = 0

#List of sales reps
repList = { 'support.csv' : '5000' }

#yesterday
#curDate = datetime.datetime.now() - datetime.timedelta(x)

#Get current date
curDate = datetime.datetime.now()
curDate = curDate.strftime("%Y-%m-%d")

for name in repList:
  mysql_query_dst = 'mysql -u root -e "use asteriskcdrdb; select calldate, src, dst, duration from cdr where calldate like \'' + str(curDate) + '%\' and dst=\'' + str(repList[name]) + '\'  into outfile \'/tmp/dst.' + name + '\'" --password=xxxxxxx'
  mysql_query_callerid = 'mysql -u root -e "use asteriskcdrdb; select calid from cdr where calldate like \'' + str(curDate) + '%\' and dst=\'' + str(repList[name]) + '\' into outfile \'/tmp/dst.callerid.' + name + '\'" --password=xxxxxx'
  print mysql_query_dst
  print mysql_query_callerid
  commands.getoutput(mysql_query_dst)
  commands.getoutput(mysql_query_callerid)

#Fix formatting of CSV files
commands.getoutput("for i in /tmp/*.csv; do sed -i 's/\\s/,/g' $i; done")

#Start reporting file
reportFile = "/tmp/report-" + curDate + ".html"
try:
  report = open(reportFile, "w")
  report.write("<HTML>\n\t<HEAD>\n")
  report.write("\t\t<style type=\"text/css\">\n")
  report.write("\t\t\t\ta { text-decoration: none; }\n")
  report.write("\t\t\t\ta:hover { text-decoration: underline; }\n")
  report.write("\t\t</style>\n")
  report.write("<TITLE> Report for " + curDate + "</TITLE>\n\t</HEAD>\n\t<BODY>\n")

except:
  print "Unable to open report file."

###############################################
# Create bulleted list of names and hyperlinks#
###############################################

for name in repList:
  duration = 0
  callCount = 0
  completeTotalCalls = 0
  completeTotalDuration = 0

  #read csv to gather average and total time of calls
  timeReader = csv.reader(open("/tmp/dst." + name, "rb"), delimiter=',')

  #get total duration and call counts

  for row in timeReader:
    callCount += 1

  #write rep name and column headers
  report.write("\t\t<TABLE style='border: 1px #d79900 solid; text-align: center'><BR>\n")
  report.write("\t\t<TR style='background-color: #CCCCCC'><TD><B> " + name + "</B>  Incoming Calls on " + curDate + "</TD></TR><TR><TD>Call Date</TD><TD>Time</TD><TD>Src</TD><TD>Dst</TD><TD>Duration</TD></TR>\n")

  #open rep data call file
  rep = open("/tmp/dst." + name, "r")

  #write each call to report file
  for line in rep:
    print "line: " + line
    spLine = line.split(',')
    duration += int(row[-1])
    completeTotalCalls += 1
    spLine[4] = str(int(spLine[4]) / 60) + " min " + str(int(spLine[4]) % 60) + " sec"
    report.write("\t\t<TR><TD>" + spLine[0] + "</TD><TD>" + spLine[1] + "</TD><TD>" + spLine[2] + "</TD><TD>" + spLine[3] + "</TD><TD>" + spLine[4] + "</TD></TR>\n")

  # Make HR line go across table to separate call count + calls
  report.write("\t\t<TR><TD colspan=5><HR></TD></TR>\n")
  report.write("\t\t<TR><TD align=left><B>Call count:</B> " + str(callCount) + "</TD></TR>\n")

  #Find service level information
  queue = commands.getoutput("/usr/sbin/asterisk -r -x 'queue show 5000'").split('\n')
  servicelevel = re.search("SL:(\d+\.\d+)% within (\d+)s", queue[0])
  holdtime = re.search("(\d+)s holdtime", queue[0])

  print "service level %: " + servicelevel.group(1)
  print "service level seconds: " + servicelevel.group(2)
  print "hold avg: " + holdtime.group(1) + " seconds."

  report.write("\t\t<TR><TD align=left>Service level: " + servicelevel.group(1) + "% of calls answered within " + servicelevel.group(2) + " seconds</TD></TR>\n")
  report.write("\t\t<TR><TD align=left>Hold time average: " + holdtime.group(1) + " seconds</TD></TR>\n")
  report.write("\t\t</TABLE>\n")

  #close rep data call file
  rep.close()




report.write("\t</BODY>\n</HTML>")
report.close()

#remove .csv files from /tmp folder
commands.getoutput("/root/removecsv.sh")

#flush queue stats
commands.getoutput("/usr/sbin/asterisk -r -x 'queue flush stats 5000'")


try:
  s = smtplib.SMTP('localhost', port=25)
except:
  print "Error connecting to smtp on localhost port 25"

mail_to = ['xxxxxxxx@peoplematter.com']
msg_report = MIMEMultipart('alternative')
msg_report['Subject'] = 'Support phone report for ' + curDate
msg_report['From'] = 'phonereport@peoplematter.com'
msg_report['To'] = COMMASPACE.join(mail_to)
msg = MIMEBase('application', 'octet-stream')
msg.set_payload(file(r'/tmp/report-' + curDate + '.html').read())
encoders.encode_base64(msg)
msg.add_header('Content-Disposition', 'attachment;filename=report-' + curDate + '.html')
msg_report.attach(msg)

try:
  print "skip mail"
  s.sendmail(msg_report['From'], mail_to, msg_report.as_string())
except:
  print "Error sending e-mail."

s.quit()

