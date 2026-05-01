import os
import io
import uuid
import pytest
import pathlib


def make_temp_app():
    import tempfile
    import sys
    import pathlib

    tmp = tempfile.NamedTemporaryFile(prefix="test_endpoints_", suffix=".db", delete=False)
    tmp.close()
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp.name}"

    project_root = str(pathlib.Path(__file__).resolve().parents[2])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Ensure fresh imports so the new DATABASE_URL is used
    for name in list(sys.modules.keys()):
        if name.startswith("management.mvc_app") or name.startswith("mvc_app") or name.startswith("management.app"):
            del sys.modules[name]

    from management.app import create_app
    from management.mvc_app.db import SessionLocal
    from management.mvc_app.upload_service import (
        process_products_upload_from_request,
        process_purchases_upload_from_request,
    )

    app = create_app()

    helpers = {
        "SessionLocal": SessionLocal,
        "process_products": process_products_upload_from_request,
        "process_purchases": process_purchases_upload_from_request,
        "tmpfile": tmp.name,
    }
    return app, helpers


class MockRequest:
    def __init__(self, fileobj):
        self.files = {"file": fileobj}


def upload_products(helper, csv_text: str):
    f = io.BytesIO(csv_text.encode("utf-8"))
    req = MockRequest(f)
    req.files["file"].seek(0)
    return helper["process_products"](req)


def upload_purchases(helper, csv_text: str):
    f = io.BytesIO(csv_text.encode("utf-8"))
    req = MockRequest(f)
    req.files["file"].seek(0)
    return helper["process_purchases"](req)


@pytest.fixture
def app_helper():
    app, helper = make_temp_app()
    # Some Werkzeug versions don't expose __version__; ensure it's present for Flask testing
    try:
        import werkzeug
        if not hasattr(werkzeug, "__version__"):
            werkzeug.__version__ = "1.0.0"
    except Exception:
        pass
    client = app.test_client()
    yield client, helper
    # teardown: remove the temporary sqlite file
    tmp = helper.get("tmpfile")
    try:
        # close any remaining sessions
        sl = helper.get("SessionLocal")
        if sl:
            s = sl()
            s.close()
    except Exception:
        pass
    try:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)
    except Exception:
        pass


def seed_data(helper):
    # prepare products
    products_csv = "product_name,unit_price\nApple,1.00\nBanana,2.00\nCherry,3.00\nDate,4.00\n"
    res = upload_products(helper, products_csv)
    assert res.success and res.inserted_count == 4

    # prepare purchases: create two users, user1 will have 4 purchases (loyal), user2 will have 2
    user1 = str(uuid.uuid4())
    user2 = str(uuid.uuid4())
    ts = '2021-01-01T00:00:00Z'

    purchases = [
        f'store1,{ts},{user1},Apple,1.00',
        f'store1,{ts},{user1},Apple,1.00',
        f'store1,{ts},{user1},Banana,2.00',
        f'store1,{ts},{user1},Cherry,3.00',
        f'store2,{ts},{user2},Banana,2.00',
        f'store2,{ts},{user2},Cherry,3.00',
        # add a Date purchase by a third user to create a distinct low count
        f'store3,{ts},{str(uuid.uuid4())},Date,4.00',
    ]

    purchases_csv = 'supermarket_id,timestamp,user_id,items_list,total_amount\n' + '\n'.join(purchases) + '\n'
    res2 = upload_purchases(helper, purchases_csv)
    assert res2.success and res2.inserted_count == len(purchases)
    return user1, user2


def test_unique_customers(app_helper):
    client, helper = app_helper
    seed_data(helper)

    rv = client.get('/unique_customers')
    assert rv.status_code == 200
    text = rv.get_data(as_text=True)
    assert 'The number of unique customers is:' in text
    assert '3' in text


def test_loyal_customers(app_helper):
    client, helper = app_helper
    user1, user2 = seed_data(helper)

    rv2 = client.get('/loyal_customers')
    assert rv2.status_code == 200
    text2 = rv2.get_data(as_text=True)
    assert user1 in text2
    assert user2 not in text2


def test_best_sellers(app_helper):
    client, helper = app_helper
    seed_data(helper)

    rv3 = client.get('/best_sellers')
    assert rv3.status_code == 200
    text3 = rv3.get_data(as_text=True)
    assert 'Apple' in text3
    assert 'Banana' in text3
    assert 'Cherry' in text3
    assert 'Date' in text3



