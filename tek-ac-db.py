from flask import Flask, request, redirect, url_for, send_from_directory, render_template
from flask.ext.basicauth import BasicAuth
import wiegand
import pickledb
import sys


app = Flask(__name__)
app.debug = True

app.config['BASIC_AUTH_USERNAME'] = sys.argv[1]
app.config['BASIC_AUTH_PASSWORD'] = sys.argv[2]

db = pickledb.load(sys.argv[3], True)

basic_auth = BasicAuth(app)

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
  return render_template('index.html', cards=db.db)

# Update card data
@app.route('/update', methods=['POST'])
def update():
  cardid = request.form['card']
  first  = request.form['first']
  last   = request.form['last']
  
  front  = request.form.get('front','')
  if front == '':
    front = False;
  else:
    front = True;
  back   = request.form.get('back','')
  if back == '':
    back = False;
  else:
    back = True;
  wood   = request.form.get('wood','')
  if wood == '':
    wood = False;
  else:
    wood = True;
  metal  = request.form.get('metal','')
  if metal == '':
    metal = False;
  else:
    metal = True;
  
  currcard = {'first': first, 'last': last, 'front':front, 'back':back, 'wood':wood, 'metal':metal}
  
  print cardid
  print currcard
  db.set(cardid,currcard);
  db.dump();
  return render_template('index.html', cards=db.db, currcard=currcard, cardid=cardid)

# View card details  
@app.route('/view/<path:card>')
def view(card):
  currcard = db.get(card)
  return render_template('index.html', cards=db.db, currcard=currcard,cardid=card)

# Add Card  
@app.route('/add', methods=['POST'])
def add():
  newcard=request.form['newcard']
  db.set(newcard,{'first': '', 'last': '', 'front':False, 'back':False, 'wood':False, 'metal':False})
  db.dump();
  
  currcard = db.get(newcard);
  return render_template('index.html', cards=db.db, currcard=currcard,cardid=newcard)
# Serve Static Files
@app.route('/<path:path>')
@basic_auth.required
def static_proxy(path):
  return app.send_static_file(path)

# Send a list of cards.
@app.route("/db")
@basic_auth.required
def getcarddb():
  return "Hello World!"

# Validate Card and then do a lookup in the DB.
# Check to see if card has permission to access.
@app.route("/access/wieg/<path:card>/<path:action>")
def access(card,action):
  # 
  try:
    c = convertWieg(card) # validate card data
    if c['site'] == 17:   # check site code
      if db.get(str(c['card']))[action] == True:
        return 'approved' # Tell reader it can open door
  except KeyError:
    return 'denied' # Unknown card. Dont open.
  except TypeError:
    return 'denied' # Unknown card. Dont open.
  except ValueError:
    return 'denied' # Invalid Data. Don't open.
  return 'denied'   # Card lacks permissions. Don't open.

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8080)
