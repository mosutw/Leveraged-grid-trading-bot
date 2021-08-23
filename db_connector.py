import mysql.connector

class db_connector:

	def __init__(self,hostname='localhost',user="",passwd="",database=""):
		self.hostname = hostname
		self.user = user
		self.passwd = passwd
		self.database = database

	def execute(self,cmd):

		mydb=mysql.connector.connect(host=self.hostname,user=self.user,auth_plugin='mysql_native_password',\
			database=self.database,passwd=self.passwd,autocommit=True)
		mycursor = mydb.cursor()
		mycursor.execute(cmd)
		msg=[]

		try:
			myresult = mycursor.fetchall()
			for x in myresult:
				tmp=[]
				for element in x:
					tmp.append(element)
				msg.append(tmp)
		finally:
			mydb.close()
			return msg