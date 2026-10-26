# ShopSmart — Day 1 starter

A beginner-friendly Flask starter for the BCA final-year project:
**E-Commerce Platform with Personalized Product Recommendations**.

## Requirements
- Windows 11
- Python 3.11 or newer
- VS Code (recommended)

## Setup on Windows PowerShell

Open PowerShell in this project folder and run:

```powershell
py --version
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

If PowerShell blocks virtual-environment activation, use Command Prompt instead:

```bat
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## Included in Day 1
- Responsive ShopSmart homepage
- Sample product catalogue
- Search by product/category/description
- Category filters
- Demo add-to-cart counter and wishlist interaction
- JSON product endpoint at `/api/products`

## Important
The cart and wishlist are UI demos and do not persist yet. The product data is temporary Python data, not a database. Later milestones will add SQLite, accounts, persistent cart/orders, and the recommendation engine. Do not deploy the Flask debug server publicly.
