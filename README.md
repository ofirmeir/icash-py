🧾 Cash Register & Management System
A simple microservices-based Python system that simulates a retail environment with:


🛒 Cash Register UI — records purchases into a PostgreSQL database


🧠 Management UI — manages product and purchase data, allows CSV uploads and queries


🗄️ PostgreSQL Database — central data store for products, purchases, and purchase items


All services run in Docker containers orchestrated with Docker Compose.

🧩 System Architecture

```text
+---------------------+        +---------------------+
|   Cash Register UI  | <----> |   PostgreSQL (DB)   |
|  Flask Microservice |        |     appdb           |
+---------------------+        +---------------------+
                                          ↑
                                          |
                                          |
+---------------------+                   |
|   Management UI     | <-----------------+
|  Flask Microservice |
+---------------------+
```
Each service runs independently inside its own container and communicates with the shared db service over the internal Docker network.

🧱 Features
Cash Register UI


Web form to record new purchases.


Each purchase includes supermarket ID, user ID, and item list.


Looks up item prices from the database and saves a normalized purchase record.



Management UI


Uploads products.csv → updates/creates product entries.


Uploads purchases.csv → imports normalized purchase data (into purchases + purchase_items).


CSV uploads validated and errors displayed in UI.


Database Schema
Normalized relational schema:
products (id, product_name, unit_price)
purchases (id, supermarket_id, timestamp, user_id, total_amount)
purchase_items (id, purchase_id, product_id, quantity, line_total)

Example data
Illustrative sample rows (4–5 rows per table). Values follow the project's SQLAlchemy models — `users.uuid` shown as UUIDs and numeric values are plain numbers.

#### products
| id | product_name | unit_price |
| ---: | :--- | ---: |
| 1 | apple | 0.50 |
| 2 | banana | 0.30 |
| 3 | milk | 2.50 |
| 4 | bread | 1.20 |

#### stores
| id | supermarket_id |
| ---: | :--- |
| 1 | SM1 |
| 2 | SM2 |

#### users
| id | uuid |
| ---: | :--- |
| 1 | 636de57b-89bc-40e4-9e9b-e008636d33ba |
| 2 | 11111111-2222-3333-4444-555555555555 |
| 3 | 9f8b7c6d-5e4f-3a2b-1c0d-abcdef123456 |

#### purchases
| id | supermarket_id (stores.id) | timestamp | user_id | total_amount |
| ---: | ---: | :--- | ---: | ---: |
| 1 | 1 | 2025-10-28T08:12:00Z | 1 | 1.00 |
| 2 | 1 | 2025-10-28T09:30:00Z | 2 | 2.50 |
| 3 | 2 | 2025-10-28T10:00:00Z | 3 | 0.60 |
| 4 | 1 | 2025-10-29T11:00:00Z | 1 | 3.70 |

#### purchase_items
| id | purchase_id | product_id | user_id | total_purchases |
| ---: | ---: | ---: | ---: |----------------:|
| 1 | 1 | 1 | 1 |               1 |
| 2 | 2 | 3 | 2 |               1 |
| 3 | 3 | 2 | 3 |               1 |
| 4 | 4 | 4 | 1 |               1 |
| 5 | 4 | 3 | 1 |               1 |


🐳 Quick Start
1. Clone the repository
git clone [https://github.com/ofirmeir/icash-py.git](https://github.com/ofirmeir/icash-py.git)
cd icash-py

2. Build and start all services
docker-compose up --build

This will start:


PostgreSQL at localhost:5432


Cash Register UI at http://localhost:5000


Management UI at http://localhost:5001


All containers wait until PostgreSQL is ready using the included wait-for-postgres.sh script.

🧾 Usage
1. Load Product Data
Open http://localhost:5001 and upload your products.csv file:
Example:
```text
product_name,unit_price
apple,0.5
banana,0.3
milk,2.5
bread,1.2
```
2. Load Purchases Data
Still in Management UI, upload purchases.csv file:
Example:
```text
supermarket_id,timestamp,user_id,items_list,total_amount
SM1,2025-10-28T08:12:00Z,636de57b-89bc-40e4-9e9b-e008636d33ba,"apple",1.0
SM1,2025-10-28T09:30:00Z,11111111-2222-3333-4444-555555555555,"banana,milk",3.4
SM2,2025-10-28T10:00:00Z,9f8b7c6d-5e4f-3a2b-1c0d-abcdef123456,"bread,milk",4.9
```

3. Get the numbers of unique customers
visit http://localhost:5000/unique_customers

4. Get the numbers of loyal customers (who bought more than 3 times, paginated)
visit http://localhost:5000/loyal_customers

5. Get a list of three product best sellers (paginated)
visit http://localhost:5000/best_sellers

6. Record Purchases via Cash Register
Visit http://localhost:5000:


Fill in supermarket ID and user ID.


Add items to the list


Complete Purchase — the purchase will be stored in the DB.


Example input:
```text
Supermarket ID: SM1
User ID: 636de57b-89bc-40e4-9e9b-e008636d33ba
Items: apple,bread
```



⚙️ Project Structure
```text
icash-py/
├── docker-compose.yaml
├── README.md
├── cash_register/
│   ├── app.py
│   ├── Dockerfile
│   ├── log.cfg
│   ├── requirements.txt
│   ├── wait-for-postgres.sh
│   ├── shared/
│   ├── mvc_app/
│   │   ├── __init__.py
│   │   ├── controllers.py
│   │   ├── db.py
│   │   ├── logging_config.py
│   │   ├── models.py
│   │   ├── templates/
│   │       ├── index.html
├── management/
│   ├── app.py
│   ├── Dockerfile
│   ├── log.cfg
│   ├── requirements.txt
│   ├── wait-for-postgres.sh
│   ├── shared/
│   ├── mvc_app/
│   │   ├── __init__.py
│   │   ├── controllers.py
│   │   ├── db.py
│   │   ├── logging_config.py
│   │   ├── models.py
│   │   ├── templates/
│   │       ├── best_sellers.html
│   │       ├── index.html
│   │       ├── loyal_customers.html
│   │       ├── unique_customers.html
│   ├── tests/
│   │   ├── requirements-dev.txt
│   │   ├── test_upload_purchases.py
├── postgres/
│   ├── init.sql
├── sample_csvs/
│   ├── products_list.csv
│   ├── purchases.csv

```

🧠 Implementation Notes


Built with Flask + SQLAlchemy for simplicity.


Uses PostgreSQL with normalized relational schema.


Both services use wait-for-postgres.sh to ensure DB readiness.


Optional healthcheck in Docker Compose can ensure better startup coordination.



🧰 Common Commands
Rebuild and restart everything
docker-compose up --build

Stop all containers
docker-compose down

Reset database
docker-compose down -v

View logs
docker-compose logs -f



🧑‍💻 Author
Ofir Me
Backend Developer — Cloud Microservices Specialist
