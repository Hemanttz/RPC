# PV Tool Training Server

This is the PV Tool Training App, a web application built with Python (Flask), SQLite, HTML, CSS, and Vanilla JavaScript.

## 🚀 Running Locally

1. Ensure you have Python installed.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python server.py
   ```
4. The server will start, and the database (`pv_app.db`) will be automatically created. You can open `http://localhost:5000` in your browser.
5. *(Optional)* If you want to seed the database with initial products from the CSV/Excel file, run:
   ```bash
   python seed_products.py
   ```

## ⚠️ Important Deployment Precautions

If you are planning to deploy this code to GitHub and host it (e.g., Render, Heroku, PythonAnywhere, Vercel), keep the following in mind:

### 1. The Database (`pv_app.db`) is Ignored
By default, the `.gitignore` prevents `pv_app.db` from being committed to GitHub.
* **Why:** You should not commit production/local databases to version control due to security and data conflict reasons.
* **What to do:** When you deploy, the server will create an empty `pv_app.db` automatically upon running `init_db()`. You will need to either upload your products using the **Add Products** admin dashboard or run `seed_products.py` on the server.

### 2. SQLite on Cloud Providers (Ephemeral File Systems)
Many modern free hosts (like Render free tier, Heroku, or Vercel) have **ephemeral file systems**.
* This means that every time the app restarts, goes to sleep, or redeploys, any changes made to `pv_app.db` (new users, new scans, new products) will be **deleted**.
* **Fix:** If you need persistent data, you should:
  * Use a host with a persistent disk (like PythonAnywhere or a VPS like DigitalOcean).
  * OR migrate from SQLite to **PostgreSQL** or **MySQL** (using SQLAlchemy) which runs as a separate service.

### 3. Change Admin Credentials!
In `database.py`, there is a hardcoded admin credential:
```python
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin@123'
```
* **Security Risk:** If your repository is public, anyone can see this password and use the upload endpoint.
* **Fix:** Change this to use Environment Variables before deploying publicly. 
  * Example: `ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'fallback')`

### 4. Uploaded Images / File Storage
The current product images are static files inside `static/products/`. 
* If you upload *new* files dynamically via the app in the future, they will also be lost on ephemeral hosts (like Render/Heroku) upon restart.
* If you plan to allow dynamic image uploads, integrate a cloud storage service like AWS S3 or Cloudinary.

## Features
- **Dashboard:** See real-time metrics, recent PV lists, and productivity stats.
- **Quality Check (QC):** Scan tracking IDs to check products and log QC decisions.
- **Add Products:** Admin portal to bulk-upload product CSVs directly to the DB.
- **Export:** Export session data for analysis.
