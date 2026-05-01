
import os
import io
import uuid


def test_upload_purchases_in_memory_sqlite():
	# Use in-memory SQLite for the test
	os.environ["DATABASE_URL"] = "sqlite:///:memory:"

	# Ensure project root is on sys.path so 'management' package is importable
	import sys
	import pathlib
	project_root = str(pathlib.Path(__file__).resolve().parents[2])
	if project_root not in sys.path:
		sys.path.insert(0, project_root)

	# Import app after setting DATABASE_URL so the engine is created for SQLite
	from management.app import create_app
	from management.mvc_app.db import SessionLocal
	from management.mvc_app.models import Product, Purchase, PurchaseItem, User, TotalUserPurchases

	app = create_app()
	# Some werkzeug versions do not expose __version__; ensure test client can read it
	try:
		import werkzeug
		if not hasattr(werkzeug, "__version__"):
			werkzeug.__version__ = "0"
	except Exception:
		pass

	client = app.test_client()

	# Prepare a small products CSV (2 products)
	products_csv = "product_name,unit_price\nApple,1.00\nBanana,2.00\n"
	data = {
		'file': (io.BytesIO(products_csv.encode('utf-8')), 'products.csv')
	}
	resp = client.post('/upload_products', data=data, content_type='multipart/form-data', follow_redirects=True)
	assert resp.status_code == 200

	# Prepare purchases CSV (4 rows, quoted items_list where needed)
	user1 = str(uuid.uuid4())
	user2 = str(uuid.uuid4())
	ts = '2021-01-01T00:00:00Z'
	purchases_csv = (
		'supermarket_id,timestamp,user_id,items_list,total_amount\n'
		f'store1,{ts},{user1},"Apple",1.00\n'
		f'store1,{ts},{user1},"Apple",1.00\n'
		f'store2,{ts},{user2},"Banana",2.00\n'
		f'store2,{ts},{user2},"Apple,Banana",3.00\n'
	)

	data = {
		'file': (io.BytesIO(purchases_csv.encode('utf-8')), 'purchases.csv')
	}
	resp = client.post('/upload_purchases', data=data, content_type='multipart/form-data', follow_redirects=True)
	assert resp.status_code == 200

	# Verify DB contents
	session = SessionLocal()
	try:
		assert session.query(Product).count() == 2
		assert session.query(Purchase).count() == 4
		assert session.query(User).count() == 2
		# each user made 2 purchases
		totals = {u.uuid: u.total_purchases.total_purchases for u in session.query(User).all()}
		assert totals[user1] == 2
		assert totals[user2] == 2

		# PurchaseItem totals per user/product
		apple = session.query(Product).filter_by(product_name='Apple').first()
		banana = session.query(Product).filter_by(product_name='Banana').first()
		u1 = session.query(User).filter_by(uuid=user1).first()
		u2 = session.query(User).filter_by(uuid=user2).first()

		pi_u1_apple = session.query(PurchaseItem).filter_by(product_id=apple.id, user_id=u1.id).first()
		assert pi_u1_apple is not None
		assert pi_u1_apple.total_purchases == 2

		pi_u2_banana = session.query(PurchaseItem).filter_by(product_id=banana.id, user_id=u2.id).first()
		assert pi_u2_banana is not None
		assert pi_u2_banana.total_purchases == 2

		pi_u2_apple = session.query(PurchaseItem).filter_by(product_id=apple.id, user_id=u2.id).first()
		assert pi_u2_apple is not None
		assert pi_u2_apple.total_purchases == 1
	finally:
		session.close()



