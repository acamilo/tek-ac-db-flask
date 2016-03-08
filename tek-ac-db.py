from flask import Flask, request, redirect, url_for, send_from_directory, render_template
from flask.ext.basicauth import BasicAuth
from datetime import date

import sys
import os

from peewee import *

db = SqliteDatabase(sys.argv[3])

app = Flask(__name__)
app.debug = True

app.config['BASIC_AUTH_USERNAME'] = sys.argv[1]
app.config['BASIC_AUTH_PASSWORD'] = sys.argv[2]

basic_auth = BasicAuth(app)

# Set up some objects for or ORM
class IDCard(Model):
  first    = CharField()
  last     = CharField()
  cardsite = IntegerField()
  cardnum  = IntegerField()
  front    = BooleanField()
  back     = BooleanField()
  wood     = BooleanField()
  metal    = BooleanField()
  
  class Meta:
    database = db

class Access(Model):
  item   = CharField()
  result = CharField()
  date   = DateField()
  card   = ForeignKeyField(IDCard, related_name='events')
  
  class Meta:
    database = db



# This function decodes the binary string sent to us by the card reader
# for our 33 bit wiegand card. 7 bit site.
def convertWieg(wiegbits):
  if len(wiegbits) != 33:
    raise ValueError('Wrong Wiegand format')
  ep   = wiegbits[0]
  op   = wiegbits[32]
  site = wiegbits[1:8]
  card = wiegbits[8:32]
  
  #Check site code parity
  if int(ep) != site.count('1')%2:
    raise ValueError('Site Code Parity Bit Invalid')
  
  if int(op) == card.count('1')%2:
    raise ValueError('Card Code Parity Bit Invalid')
  
  # Code looks good. Convert to integer
  siteid = int(site,2)
  cardid = int(card,2)
  
  return {'site':siteid,'card':cardid}

#Admin app
@app.route('/')
@basic_auth.required
def root():
  return render_template('index.html', cards=IDCard.select())

# Update card data
@app.route('/update', methods=['POST'])
def update():
  
  cardid = request.form['card']
  # Lookup card by ID
  currcard = IDCard.get(IDCard.cardnum == cardid)
  # update info
  currcard.first  = request.form['first']
  currcard.last   = request.form['last']
  currcard.front  = request.form.get('front','') == 'on'
  currcard.back   = request.form.get('back','')  == 'on'
  currcard.wood   = request.form.get('wood','')  == 'on'
  currcard.metal  = request.form.get('metal','') == 'on'
  # Save to DB
  currcard.save()
  return render_template('index.html', cards=IDCard.select(), currcard = currcard)

# View card details  
@app.route('/view/<path:card>')
def view(card):
  currcard = IDCard.get(IDCard.cardnum == card)
  return render_template('index.html', cards=IDCard.select(),currcard = currcard)

# Add Card  
@app.route('/add', methods=['POST'])
def add():
  cardnum=request.form['newcard']
  # Create new card and push to DB
  newcard = IDCard(first='',last='',cardsite=17,cardnum=cardnum,front=False,back=False,wood=False,metal=False)
  newcard.save()
  return render_template('index.html', cards=IDCard.select(), currcard = newcard)

# Serve Static Files
@app.route('/<path:path>')
@basic_auth.required
def static_proxy(path):
  return app.send_static_file(path)

# Validate Card and then do a lookup in the DB.
# Check to see if card has permission to access.
@app.route("/access/wieg/<path:card>/<path:action>")
def access(card,action):
  # 
  try:
    c = convertWieg(card) # validate card data
    if c['site'] == 17:   # check site code
      currcard = IDCard.get(IDCard.cardnum == c['card'])
      if getattr(currcard,action):
        return 'approved' # Tell reader it can open door
  except:
    return 'denied' # Invalid Data. Don't open.
  return 'denied'   # Card lacks permissions. Don't open.

if __name__ == "__main__":
  #Does DB exist?
  if os.path.isfile(sys.argv[3])==False:
    print "Initializing empty database."
    db.connect()
    db.create_tables([IDCard, Access])
  else:
    print "Opening existing database"
    db.connect()
  
  
    
  app.run(host='0.0.0.0', port=8080)
