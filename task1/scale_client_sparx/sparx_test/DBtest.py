import peewee

db = peewee.MySQLDatabase("scale_client",user="scale_usr",passwd="admin")

try:
	db.connect()
except peewee.OperationalError, err:
	print(err)
