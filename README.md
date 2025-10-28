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
           ↓
+---------------------+
|   Management UI     |
|  Flask Microservice |
+---------------------+
```
Each service runs independently inside its own container and communicates with the shared db service over the internal Docker network.

🧱 Features
Cash Register UI


Web form to record new purchases.


Each purchase includes supermarket ID, user ID, and item list.


Looks up item prices from the database and saves a normalized purchase record.


Endpoint /recent to fetch the most recent purchase as JSON.


Management UI


Uploads products.csv → updates/creates product entries.


Uploads purchases.csv → imports normalized purchase data (into purchases + purchase_items).


Endpoint /recent → returns most recent purchase in the database.


CSV uploads validated and errors displayed in UI.


Database Schema
Normalized relational schema:
products (id, product_name, unit_price)
purchases (id, supermarket_id, timestamp, user_id, total_amount)
purchase_items (id, purchase_id, product_id, quantity, line_total)


🐳 Quick Start
1. Clone the repository
git clone https://github.com/yourname/cash-register-management.git
cd cash-register-management

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
product_name,unit_price
apple,0.5
banana,0.3
milk,2.5
bread,1.2


2. (Optional) Load Purchases Data
Still in Management UI, upload purchases.csv file:
Example:
```text
supermarket_id,timestamp,user_id,items_list,total_amount
SM1,2025-10-28T08:12:00Z,u001,apple:2,1.0
SM1,2025-10-28T09:30:00Z,u002,banana:3,milk:1,3.4
SM2,2025-10-28T10:00:00Z,u003,bread:2,milk:1,4.9
```

4. Record Purchases via Cash Register
Visit http://localhost:5000:


Fill in supermarket ID and user ID.


Enter items list (format: product_name:quantity,product_name:quantity)


Submit — the purchase will be stored in the DB.


Example input:
```text
Supermarket ID: SM1
User ID: u100
Items: apple:3,bread:1
```

4. Query the Most Recent Purchase
Either UI exposes a JSON endpoint:
GET /recent

Example response:
```text
{
  "id": 5,
  "supermarket_id": "SM1",
  "timestamp": "2025-10-28T09:30:00Z",
  "user_id": "u002",
  "total_amount": "3.40",
  "items": [
    {"product_name": "banana", "unit_price": "0.30", "quantity": 3, "line_total": "0.90"},
    {"product_name": "milk", "unit_price": "2.50", "quantity": 1, "line_total": "2.50"}
  ]
}
```

⚙️ Project Structure
```text
cash-register-management/
├── docker-compose.yml
├── postgres/
│   └── init.sql
├── cash_register/
│   ├── Dockerfile
│   ├── app.py
│   ├── requirements.txt
│   └── wait-for-postgres.sh
├── management/
│   ├── Dockerfile
│   ├── app.py
│   ├── requirements.txt
│   └── wait-for-postgres.sh
└── sample_csvs/
    ├── products.csv
    └── purchases.csv
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


🧩 Future Enhancements


📊 Add dashboard in Management UI (e.g., top products, revenue per day)


✅ Add preview before importing purchases


🧮 Add automatic data validation and error reports


📦 Implement authentication between services



🧑‍💻 Author
Ofir Me
Python Developer — Cloud Microservices Specialist
(replace with your actual name and contact info if needed)

Would you like me to include badges (Docker, Python, Flask, PostgreSQL, License, etc.) at the top of the README for a polished GitHub presentation?
