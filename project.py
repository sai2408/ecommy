from flask import Flask,render_template,request,flash,redirect,url_for,session,Response
import mysql.connector
from flask_session import Session
from otp import genotp
from stoken import token,dtoken
from cmail import sendmail
import os
import razorpay
import re
import pdfkit
app=Flask(__name__)
app.config['SESSION_TYPE']='filesystem'
config=pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
RAZORPAY_KEY_ID='rzp_test_RXy19zNlFo9p8F'
RAZORPAY_KEY_SECRET='eIHxmEyJqhKz2l0tHEy7KkkC'
client=razorpay.Client(auth=(RAZORPAY_KEY_ID,RAZORPAY_KEY_SECRET))
mydb=mysql.connector.connect(host='localhost',username='root',password='Admin',db='ecommy')
app.secret_key=b'\x8e\xe0\xa5\xd9\x9c'
@app.route('/')
def home():
    return render_template('welcome.html')
@app.route('/index')
def index():
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select bin_to_uuid(item_id),item_name,image_name,price,quantity,category,description from items')
    item_data=cursor.fetchall()
    print(item_data)
    return render_template('index.html',item_data=item_data)
#admin-loginsystem
@app.route('/admincreate',methods=['GET','POST'])
def admincreate():
    if request.method=='POST':
        username=request.form['username']
        email=request.form['email']
        password=request.form['password']
        address=request.form['address']
        accept=request.form['agree']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from admincreate where email=%s',[email])
        email_count=cursor.fetchone()[0]
        if email_count==0:
            otp=genotp()
            data={'username':username,'email':email,'password':password,'address':address,'accept':accept,'otp':otp}
            subject='Admin verify for BUYROUTE'
            body=f'Use this otp for verification {otp}'
            sendmail(email=email,subject=subject,body=body)
            flash('OTP has been sent to given mail')
            return redirect(url_for('adminverify',var1=token(data=data)))
        elif email_count==1:
            flash('Email ALready existed')
            return redirect(url_for('adminlogin'))
        else:
            return 'something went wrong'
    return render_template('admincreate.html')
@app.route('/adminverify/<var1>',methods=['GET','POST'])
def adminverify(var1):
    try:
        regdata=dtoken(data=var1)
    except Exception as e:
        print(e)
        return 'Something went wrong.'
    else:
        if request.method=='POST':
            uotp=request.form['otp']
            if uotp==regdata['otp']:
                print(regdata['accept'])
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into admincreate(email,username,password,address,accept) values(%s,%s,%s,%s,%s)',[regdata['email'],regdata['username'],regdata['password'],regdata['address'],regdata['accept']])
                mydb.commit()
                cursor.close()
                flash(f"{regdata['email']} Registration successfully Done")
                return redirect(url_for('adminlogin'))
            else:
                return 'Wrong OTP'
    return render_template('adminotp.html')
@app.route('/adminlogin',methods=['GET','POST'])
def adminlogin():
    if session.get('email'):
        return redirect(url_for('adminpanel'))
    else:
        if request.method=='POST':
            email=request.form['email']
            password=request.form['password']
            password=password.encode('utf-8')
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from admincreate where email=%s',[email])
            count=cursor.fetchone()
            print(count)
            if count:
                if count[0]==1:
                    cursor.execute('select password from admincreate where email=%s',[email])
                    dbpassword=cursor.fetchone()
                    print(dbpassword)
                    if dbpassword:
                        if dbpassword[0]==password:
                            session['email']=email
                            return redirect(url_for('adminpanel'))
                        else:
                            flash('Wrong password.')
                    else:
                        flash('invalid Input for password')
                        return redirect(url_for('adminlogin'))
                else:
                    flash('Wrong Email')
                    return redirect(url_for('adminlogin'))
            else:
                flash('Invalid Input for email.')
                return redirect(url_for('adminlogin'))
    return render_template('adminlogin.html')
@app.route('/adminpanel')
def adminpanel():
    return render_template('adminpanel.html')
@app.route('/additem',methods=['GET','POST'])
def additem():
    if not session.get('email'):
        return redirect(url_for('adminlogin'))
    else:
        if request.method=='POST':
            item_name=request.form['title']
            description=request.form['Discription']
            quantity=request.form['quantity']
            category=request.form['category']
            file=request.files['file']
            price=request.form['price']
            filename=genotp()+'.'+file.filename.split('.')[-1]
            path=os.path.dirname(os.path.abspath(__file__))
            print(path)
            static_path=os.path.join(path,'static')
            print(static_path)
            file.save(os.path.join(static_path,filename))
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into items(item_id,item_name,description,price,quantity,image_name,added_by,category) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s,%s)',[item_name,description,price,quantity,filename,session.get('email'),category])
            mydb.commit()
            cursor.close()
            flash(f'Item {item_name} added successfully')
    return render_template('additem.html')      
@app.route('/adminlogout')
def adminlogout():
    if session.get('email'):
        session.pop('email')
        return redirect(url_for('adminlogin'))
    else:
        return redirect(url_for('adminlogin'))

@app.route('/viewall_items')
def viewall_items():
    if not session.get('email'):
        return redirect(url_for('adminlogin'))
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,image_name from items where added_by=%s',[session.get('email')])
        item_data=cursor.fetchall()
        print(item_data)
        if item_data:
            return render_template('viewall_items.html',item_data=item_data)
        else:
            return 'No items added.'
@app.route('/view_item/<itemid>')
def view_item(itemid):
    if not session.get('email'):
        return redirect(url_for('adminlogin'))
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,image_name,price,quantity,category,description from items where added_by=%s and item_id=uuid_to_bin(%s)',[session.get('email'),itemid])
        item_data=cursor.fetchone()
        cursor.close()
        if item_data:
            return render_template('view_item.html',item_data=item_data)
        else:
            return 'something went wrong' 
@app.route('/delete_item/<itemid>')
def delete_item(itemid):
    if not session.get('email'):
        return redirect(url_for('adminlogin'))
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('delete from items where added_by=%s and item_id=uuid_to_bin(%s)',[session.get('email'),itemid])
        mydb.commit()
        cursor.close()
        flash(f'{itemid} deleted successfully.')
        return redirect(url_for('viewall_items'))
@app.route('/update_item/<itemid>',methods=['GET','POST'])
def update_item(itemid):
    if not session.get('email'):
        return redirect(url_for('adminlogin'))
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,image_name,price,quantity,category,description from items where added_by=%s and item_id=uuid_to_bin(%s)',[session.get('email'),itemid])
        item_data=cursor.fetchone()
        cursor.close()
        if request.method=='POST':
            item_name=request.form['title']
            description=request.form['Discription']
            quantity=request.form['quantity']
            category=request.form['category']
            file=request.files['file']
            price=request.form['price']
            if file.filename=='':
                filename=item_data[2]
            else:
                filename=genotp()+'.'+file.filename.split('.')[-1]
                path=os.path.dirname(os.path.abspath(__file__))                
                static_path=os.path.join(path,'static')
                os.remove(os.path.join(static_path,item_data[2]))
                file.save(os.path.join(static_path,filename))
            cursor=mydb.cursor(buffered=True)
            cursor.execute('update items set item_name=%s,description=%s,price=%s,quantity=%s,image_name=%s,category=%s where added_by=%s and item_id=uuid_to_bin(%s)',[item_name,description,price,quantity,filename,category,session.get('email'),itemid])
            mydb.commit()
            cursor.close()
            flash(f'item with {itemid} updated successfully')
            return redirect(url_for('update_item',itemid=itemid))
        if item_data:
            return render_template('update_item.html',item_data=item_data)
        else:
            return 'something went wrong '
@app.route('/adminprofile_update',methods=['GET','POST'])  
def adminprofile_update():
    if not session.get('email'):
        return redirect(url_for('adminlogin'))
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select username,address,dp_image,ph_no from admincreate where email=%s',[session.get('email')])
        admin_data=cursor.fetchone()
        cursor.close()
        if request.method=='POST':
            username=request.form['adminname']
            address=request.form['address']
            ph_no=request.form['ph_no']
            image=request.files['file']
            if image.filename=='':
                filename=admin_data[2]
            else:
                filename=genotp()+'.'+image.filename.split('.')[-1]
                path=os.path.dirname(os.path.abspath(__file__))                
                static_path=os.path.join(path,'static')
                if admin_data[2]:
                    os.remove(os.path.join(static_path,admin_data[2]))
                image.save(os.path.join(static_path,filename))
            cursor=mydb.cursor(buffered=True)
            cursor.execute('update admincreate set username=%s,address=%s,dp_image=%s,ph_no=%s where email=%s',[username,address,filename,ph_no,session.get('email')])
            mydb.commit()
            cursor.close()
            flash(f"{session.get('email')} Profile updated successfully")
            return redirect(url_for('adminprofile_update'))

        if admin_data:
            return render_template('adminupdate.html',admin_data=admin_data)
        else:
            return 'Something went wrong'
@app.route('/usercreate',methods=['GET','POST'])
def usercreate():
    if request.method=='POST':
        username=request.form['name']
        email=request.form['email']
        address=request.form['address']
        password=request.form['password']
        gender=request.form['usergender']
        print(request.form)
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from usercreate where user_email=%s',[email])
        email_count=cursor.fetchone()[0]
        if email_count==0:
            otp=genotp()
            data={'username':username,'email':email,'password':password,'address':address,'gender':gender,'otp':otp}
            subject='user verify for BUYROUTE'
            body=f'Use this otp for verification {otp}'
            sendmail(email=email,subject=subject,body=body)
            flash('OTP has been sent to given mail')
            return redirect(url_for('userverify',var1=token(data=data)))
        elif email_count==1:
            flash('Email ALready existed')
            return redirect(url_for('userlogin'))
        else:
            return 'something went wrong'
    return render_template('usersignup.html')
@app.route('/userverify/<var1>',methods=['GET','POST'])
def userverify(var1):
    try:
        regdata=dtoken(data=var1)
    except Exception as e:
        print(e)
        return 'Something went wrong.'
    else:
        if request.method=='POST':
            uotp=request.form['otp']
            if uotp==regdata['otp']:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into usercreate(user_email,username,password,address,gender) values(%s,%s,%s,%s,%s)',[regdata['email'],regdata['username'],regdata['password'],regdata['address'],regdata['gender']])
                mydb.commit()
                cursor.close()
                flash(f"{regdata['email']} Registration successfully Done")
                return redirect(url_for('userlogin'))
            else:
                return 'Wrong OTP'
    return render_template('userotp.html')
@app.route('/userlogin',methods=['GET','POST'])
def userlogin():
    if session.get('useremail'):
        return redirect(url_for('index'))
    else:
        if request.method=='POST':
            uemail=request.form['email']
            password=request.form['password']
            password=password.encode('utf-8')
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from usercreate where user_email=%s',[uemail])
            count=cursor.fetchone()
            print(count)
            if count:
                if count[0]==1:
                    cursor.execute('select password from usercreate where user_email=%s',[uemail])
                    dbpassword=cursor.fetchone()
                    print(dbpassword)
                    if dbpassword:
                        if dbpassword[0]==password:
                            session['useremail']=uemail
                            if not session.get(uemail):
                                session[uemail]={}
                                return redirect(url_for('index'))
                        else:
                            flash('Wrong password.')
                    else:
                        flash('invalid Input for password')
                        return redirect(url_for('userlogin'))
                else:
                    flash('Wrong Email')
                    return redirect(url_for('userlogin'))
            else:
                flash('Invalid Input for email.')
                return redirect(url_for('userlogin'))
    return render_template('userlogin.html')
@app.route('/dashboard/<category>')
def dashboard(category):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select bin_to_uuid(item_id),item_name,description,price,quantity,image_name,category from items where category=%s',[category])
    cursor.close()
    items_data=cursor.fetchall()
    if items_data:
        return render_template('dashboard.html',items_data=items_data)
    else:
        return 'items not found'
@app.route('/description/<itemid>')
def description(itemid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select bin_to_uuid(item_id),item_name,description,price,category,image_name,quantity from items where item_id=uuid_to_bin(%s)',[itemid])
    item_data=cursor.fetchone()
    cursor.close()
    if item_data:
        return render_template('description.html',item_data=item_data)
    else:
        return 'no item found'
@app.route('/addreview/<itemid>',methods=['GET','POST'])
def addreview(itemid):
    if session.get('useremail'):
        if request.method=='POST':
            title=request.form['title']
            reviewtext=request.form['review']
            rating=request.form['rate']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into reviews(username,itemid,title,review,rating) values(%s,uuid_to_bin(%s),%s,%s,%s)',[session.get('useremail'),itemid,title,reviewtext,rating])
            mydb.commit()
            cursor.close()
            flash(f'Review has given to {itemid}')
            return redirect(url_for('description',itemid=itemid))
        return render_template('review.html')
    else:
        return redirect(url_for('userlogin'))
@app.route('/readreview/<itemid>')
def readreview(itemid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select * from reviews where itemid=uuid_to_bin(%s)',[itemid])
    data=cursor.fetchall()
    cursor.execute('select bin_to_uuid(item_id),item_name,description,price,category,image_name,quantity from items where item_id=uuid_to_bin(%s)',[itemid])
    item_data=cursor.fetchone()
    cursor.close()
    if item_data and data:
        return render_template('readreview.html',data=data,item_data=item_data)
    else:
        flash('No reviews found')
        return redirect(url_for('description',itemid=itemid))
@app.route('/addcart/<itemid>/<name>/<category>/<float:price>/<image>/<quantity>')
def addcart(itemid,name,category,price,image,quantity):
    if not session.get('useremail'):
        return redirect(url_for('userlogin'))
    else:
        print(session)
        if itemid not in session['useremail']:
            session[session.get('useremail')][itemid]=[name,price,1,image,category]
            session.modified=True 
            flash(f"{name} added to cart")
            return redirect(url_for('index'))
        session[session.get('useremail')][itemid][2]+=1
        flash('item already existed')
        return redirect(url_for('index'))
@app.route('/viewcart')
def viewcart():
    if not session.get('useremail'):
        return redirect(url_for('userlogin'))
    if session.get(session.get('useremail')):
        items=session[session.get('useremail')]
    else: 
        items='empty'
    if items=='empty':
        return 'No Products added to cart'
    return render_template('cart.html',items=items)
@app.route('/remove/<itemid>')
def remove(itemid):
    if session.get('useremail'):
        session[session.get('useremail')].pop(itemid)
        session.modified=True
        return redirect(url_for('viewcart'))
    return redirect(url_for('userlogin'))
@app.route('/userlogout')
def userlogout():
    if session.get('useremail'):
        session.pop('useremail')
        return redirect(url_for('userlogin'))
    return redirect(url_for('userlogin'))
@app.route('/pay/<itemid>/<name>/<float:price>',methods=['GET','POST'])
def pay(itemid,name,price):
    try:
    
        qyt=int(request.form['qyt'])
        amount=price*100 #convert price into paise
        total_price=amount*qyt
        print(amount,qyt,total_price)
        print(f'creating payment for item:{itemid}, name :{name},price:{total_price}')
        #create Razorpay order
        order=client.order.create({
            'amount':total_price,
            'currency':'INR',
            'payment_capture':'1'
        })
        print(f"order created: {order}")
        return render_template('pay.html',order=order,itemid=itemid,name=name,price=total_price,qyt=qyt)
    except Exception as e:
        #Log the error and return a 400 response
        print(f'Error creating order: {str(e)}')
        return str(e),400
@app.route('/success',methods=['POST'])
def success():
    #extract payment details from the form
    payment_id=request.form.get('razorpay_payment_id')
    order_id=request.form.get('razorpay_order_id')
    signature=request.form.get('razorpay_signature')
    name=request.form.get('name')
    itemid=request.form.get('itemid')
    total_price=request.form.get('total_price')
    qyt=request.form.get('qyt')
    #verification process
    params_dict = {
        'razorpay_order_id':order_id,
        'razorpay_payment_id':payment_id,
        'razorpay_signature':signature
    }
    try:
        client.utility.verify_payment_signature(params_dict)
        cursor=mydb.cursor(buffered=True)
        cursor.execute('insert into orders(itemid,item_name,total_price,user,qty) values(uuid_to_bin(%s),%s,%s,%s,%s)',[itemid,name,total_price,session.get('useremail'),qyt])
        mydb.commit()
        cursor.close()
        flash('order placed successfully')
        return redirect(url_for('orders'))
    except razorpay.errors.SignatureVerificationError:
        return 'Payment verification failed!',400
@app.route('/orders')
def orders():
    if session.get('useremail'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select * from orders where user=%s',[session.get('useremail')])
        user_orders=cursor.fetchall()
        cursor.close()
        return render_template('orders.html',user_orders=user_orders)
    else:
        return redirect(url_for('userlogin'))
@app.route('/search',methods=['GET','POST'])
def search():
    if request.method=='POST':
        name=request.form['search']
        strg=['A-Za-z0-9']
        pattern=re.compile(f'{strg}',re.IGNORECASE)
        if (pattern.match(name)):
            cursor=mydb.cursor(buffered=True)
            query='select bin_to_uuid(item_id),item_name,description,price,quantity,image_name,added_by,category from items where item_name like %s or description like %s or price like %s or category like %s'
            search_pram=f'%{name}%'
            cursor.execute(query,[search_pram,search_pram,search_pram,search_pram])
            data=cursor.fetchall()
            return render_template('dashboard.html',items_data=data)
        else:
            flash('Result not found')
    return render_template('index.html')
@app.route('/contactus',methods=['GET','POST'])
def contactus():
    if request.method=='POST':
        name=request.form['title']
        email=request.form['email']
        message=request.form['description']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('insert into contactus values(%s,%s,%s)',[name,email,message])
        mydb.commit()
        cursor.close()
        return redirect(url_for('contactus'))
    return render_template('contact.html')
@app.route('/billdetails/<ordid>.pdf')
def invoice(ordid):
    if session.get('useremail'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select * from orders where orderid=%s',[ordid])
        orders=cursor.fetchone()
        username=orders[5]
        oname=orders[2]
        qty=orders[3]
        cost=orders[4]
        cursor.execute('select username,address,user_email from usercreate where user_email=%s',[username])
        data=cursor.fetchone()
        uname=data[0]
        uaddress=data[1]
        html=render_template('bill.html',uname=uname,uaddress=uaddress,oname=oname,qty=qty,cost=cost)
        pdf=pdfkit.from_string(html,False,configuration=config)
        response=Response(pdf,content_type='application/pdf')
        response.headers['Content-Disposition']='inline; filename=output.pdf'
        return response
app.run(debug=True,use_reloader=True)